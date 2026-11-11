#include "wifi_board.h"
#include "codecs/no_audio_codec.h"
#include "display/oled_display.h"
#include "system_reset.h"
#include "application.h"
#include "button.h"
#include "config.h"
#include "mcp_server.h"
#include "lamp_controller.h"
#include "led/single_led.h"
#include "assets/lang_config.h"

#include <esp_log.h>
#include <driver/i2c_master.h>
#include <esp_lcd_panel_ops.h>
#include <esp_lcd_panel_vendor.h>

#ifdef SH1106
#include <esp_lcd_panel_sh1106.h>
#endif

#include <material_symbols.h>
#include <esp_heap_caps.h>
#include <esp_random.h>
#include <cstring>

#include "mate_faces.h"

#define TAG "CompactWifiBoard"

LV_FONT_DECLARE(font_material_symbols_30_1);

// Mate 1 (128x64 only):
// - 3-second welcome screen at boot, drawn on top of the normal UI.
// - Butler faces (monocle and mustache) covering the content area, with a random blink.
//   The ~20 cloud emotions are grouped into 10 faces (see FaceFor).
// - A non-empty "system" message (activation code, Wi-Fi setup, errors) hides the face so its
//   text stays readable. Conversation text stays hidden behind the face.
class MateOledDisplay : public OledDisplay {
public:
    using OledDisplay::OledDisplay;

    ~MateOledDisplay() {
        if (blink_timer_ != nullptr) {
            DisplayLockGuard lock(this);
            lv_timer_delete(blink_timer_);
        }
    }

    void SetupUI() override {
        bool first_call = !IsSetupUICalled();
        OledDisplay::SetupUI();
        if (first_call && height_ >= 64) {
            CreateFaces();
            ShowSplash();
        }
    }

    bool SetEmotion(const char* emotion) override {
        bool shown = OledDisplay::SetEmotion(emotion);
        if (face_image_ == nullptr) {
            return shown;
        }
        DisplayLockGuard lock(this);
        current_face_ = FaceFor(emotion);
        eyes_closed_ = false;
        lv_image_set_src(face_image_, &open_dsc_[current_face_]);
        ScheduleBlink();
        return true;
    }

    void SetChatMessage(const char* role, const char* content) override {
        OledDisplay::SetChatMessage(role, content);
        if (face_image_ == nullptr || role == nullptr || strcmp(role, "system") != 0) {
            return;
        }
        DisplayLockGuard lock(this);
        if (content != nullptr && content[0] != '\0') {
            lv_obj_add_flag(face_image_, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_remove_flag(face_image_, LV_OBJ_FLAG_HIDDEN);
        }
    }

private:
    lv_obj_t* face_image_ = nullptr;
    lv_timer_t* blink_timer_ = nullptr;
    lv_image_dsc_t open_dsc_[mate_faces::kCount] = {};
    lv_image_dsc_t blink_dsc_[mate_faces::kBlinkCount] = {};
    mate_faces::Face current_face_ = mate_faces::kNeutral;
    bool eyes_closed_ = false;

    static mate_faces::Face FaceFor(const char* emotion) {
        using namespace mate_faces;
        struct Entry {
            const char* name;
            Face face;
        };
        static const Entry kMap[] = {
            {"happy", kHappy},         {"relaxed", kHappy},      {"delicious", kHappy},
            {"confident", kHappy},     {"sad", kSad},            {"crying", kSad},
            {"embarrassed", kSad},     {"surprised", kSurprised}, {"shocked", kSurprised},
            {"thinking", kThinking},   {"confused", kThinking},  {"angry", kAngry},
            {"laughing", kLaughing},   {"funny", kLaughing},     {"loving", kLoving},
            {"kissy", kLoving},        {"sleepy", kSleepy},      {"winking", kWinking},
            {"silly", kWinking},       {"cool", kWinking},
        };
        if (emotion != nullptr) {
            for (const auto& entry : kMap) {
                if (strcmp(entry.name, emotion) == 0) {
                    return entry.face;
                }
            }
        }
        return kNeutral;
    }

    // Expands the 1-bit faces into RGB565 frames in PSRAM (about 200 KB) and creates the
    // image object. If memory is short, Mate keeps the stock small emoji instead.
    void CreateFaces() {
        using namespace mate_faces;
        const uint32_t stride = kWidth * sizeof(uint16_t);
        const uint32_t frame_pixels = kWidth * kHeight;
        const int frames = kCount + kBlinkCount;
        auto* pixels = static_cast<uint16_t*>(heap_caps_malloc(
            frame_pixels * sizeof(uint16_t) * frames, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
        if (pixels == nullptr) {
            ESP_LOGW(TAG, "Mate faces disabled: not enough PSRAM");
            return;
        }
        for (int i = 0; i < frames; i++) {
            const uint8_t* bits = i < kCount ? kOpen[i] : kBlink[i - kCount];
            uint16_t* frame = pixels + i * frame_pixels;
            for (uint32_t p = 0; p < frame_pixels; p++) {
                bool lit = bits[p / 8] & (0x80 >> (p % 8));
                frame[p] = lit ? 0x0000 : 0xFFFF;  // On this OLED, black is a lit pixel
            }
            lv_image_dsc_t& dsc = i < kCount ? open_dsc_[i] : blink_dsc_[i - kCount];
            dsc.header.magic = LV_IMAGE_HEADER_MAGIC;
            dsc.header.cf = LV_COLOR_FORMAT_RGB565;
            dsc.header.w = kWidth;
            dsc.header.h = kHeight;
            dsc.header.stride = stride;
            dsc.data_size = stride * kHeight;
            dsc.data = reinterpret_cast<const uint8_t*>(frame);
        }

        DisplayLockGuard lock(this);
        face_image_ = lv_image_create(lv_screen_active());
        lv_obj_set_pos(face_image_, 0, 16);
        lv_image_set_src(face_image_, &open_dsc_[kNeutral]);
        blink_timer_ = lv_timer_create(BlinkTimerCallback, 4000, this);
        ScheduleBlink();
    }

    // Must be called with the display lock held.
    void ScheduleBlink() {
        if (blink_timer_ == nullptr) {
            return;
        }
        lv_timer_set_period(blink_timer_, 3000 + esp_random() % 3001);
        lv_timer_reset(blink_timer_);
    }

    static void BlinkTimerCallback(lv_timer_t* timer) {
        static_cast<MateOledDisplay*>(lv_timer_get_user_data(timer))->OnBlinkTimer();
    }

    // Runs in the LVGL task, which already holds the display lock.
    void OnBlinkTimer() {
        int blink = mate_faces::kBlinkIndex[current_face_];
        if (eyes_closed_) {
            eyes_closed_ = false;
            lv_image_set_src(face_image_, &open_dsc_[current_face_]);
            ScheduleBlink();
        } else if (blink >= 0 && !lv_obj_has_flag(face_image_, LV_OBJ_FLAG_HIDDEN)) {
            eyes_closed_ = true;
            lv_image_set_src(face_image_, &blink_dsc_[blink]);
            lv_timer_set_period(blink_timer_, 150);
            lv_timer_reset(blink_timer_);
        } else {
            ScheduleBlink();
        }
    }

    void ShowSplash() {
        DisplayLockGuard lock(this);

        lv_obj_t* splash = lv_obj_create(lv_screen_active());
        lv_obj_remove_style_all(splash);
        lv_obj_remove_flag(splash, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_size(splash, LV_HOR_RES, LV_VER_RES);
        lv_obj_set_style_bg_color(splash, lv_color_white(), 0);
        lv_obj_set_style_bg_opa(splash, LV_OPA_COVER, 0);
        lv_obj_set_flex_flow(splash, LV_FLEX_FLOW_COLUMN);
        lv_obj_set_flex_align(splash, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER,
                              LV_FLEX_ALIGN_CENTER);
        lv_obj_set_style_pad_row(splash, 2, 0);

        lv_obj_t* icon = lv_label_create(splash);
        lv_obj_set_style_text_font(icon, &font_material_symbols_30_1, 0);
        lv_label_set_text(icon, MATERIAL_SYMBOLS_ROBOT_2);

        lv_obj_t* name = lv_label_create(splash);
        lv_label_set_text(name, "Mate 1");

        lv_obj_delete_delayed(splash, 3000);
    }
};

class CompactWifiBoard : public WifiBoard {
private:
    i2c_master_bus_handle_t display_i2c_bus_;
    esp_lcd_panel_io_handle_t panel_io_ = nullptr;
    esp_lcd_panel_handle_t panel_ = nullptr;
    Display* display_ = nullptr;
    Button boot_button_;
    Button touch_button_;
    Button volume_up_button_;
    Button volume_down_button_;

    void InitializeDisplayI2c() {
        i2c_master_bus_config_t bus_config = {
            .i2c_port = (i2c_port_t)0,
            .sda_io_num = DISPLAY_SDA_PIN,
            .scl_io_num = DISPLAY_SCL_PIN,
            .clk_source = I2C_CLK_SRC_DEFAULT,
            .glitch_ignore_cnt = 7,
            .intr_priority = 0,
            .trans_queue_depth = 0,
            .flags = {
                .enable_internal_pullup = 1,
            },
        };
        ESP_ERROR_CHECK(i2c_new_master_bus(&bus_config, &display_i2c_bus_));
    }

    void InitializeSsd1306Display() {
        // SSD1306 config
        esp_lcd_panel_io_i2c_config_t io_config = {
            .dev_addr = 0x3C,
            .scl_speed_hz = 400 * 1000,
            .control_phase_bytes = 1,
            .dc_bit_offset = 6,
            .lcd_cmd_bits = 8,
            .lcd_param_bits = 8,
            .on_color_trans_done = nullptr,
            .user_ctx = nullptr,
            .flags = {
                .dc_low_on_data = 0,
                .disable_control_phase = 0,
            },
        };

        ESP_ERROR_CHECK(esp_lcd_new_panel_io_i2c(display_i2c_bus_, &io_config, &panel_io_));

        ESP_LOGI(TAG, "Install SSD1306 driver");
        esp_lcd_panel_dev_config_t panel_config = {};
        panel_config.reset_gpio_num = GPIO_NUM_NC;
        panel_config.bits_per_pixel = 1;

        esp_lcd_panel_ssd1306_config_t ssd1306_config = {
            .height = static_cast<uint8_t>(DISPLAY_HEIGHT),
        };
        panel_config.vendor_config = &ssd1306_config;

#ifdef SH1106
        ESP_ERROR_CHECK(esp_lcd_new_panel_sh1106(panel_io_, &panel_config, &panel_));
#else
        ESP_ERROR_CHECK(esp_lcd_new_panel_ssd1306(panel_io_, &panel_config, &panel_));
#endif
        ESP_LOGI(TAG, "SSD1306 driver installed");

        // Reset the display
        ESP_ERROR_CHECK(esp_lcd_panel_reset(panel_));
        if (esp_lcd_panel_init(panel_) != ESP_OK) {
            ESP_LOGE(TAG, "Failed to initialize display");
            display_ = new NoDisplay();
            return;
        }
        ESP_ERROR_CHECK(esp_lcd_panel_invert_color(panel_, false));

        // Set the display to on
        ESP_LOGI(TAG, "Turning display on");
        ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(panel_, true));

        display_ = new MateOledDisplay(panel_io_, panel_, DISPLAY_WIDTH, DISPLAY_HEIGHT, DISPLAY_MIRROR_X, DISPLAY_MIRROR_Y);
    }

    void InitializeButtons() {
        boot_button_.OnClick([this]() {
            auto& app = Application::GetInstance();
            if (app.GetDeviceState() == kDeviceStateStarting) {
                EnterWifiConfigMode();
                return;
            }
            app.ToggleChatState();
        });
        touch_button_.OnPressDown([this]() {
            Application::GetInstance().StartListening();
        });
        touch_button_.OnPressUp([this]() {
            Application::GetInstance().StopListening();
        });

        volume_up_button_.OnClick([this]() {
            auto codec = GetAudioCodec();
            auto volume = codec->output_volume() + 10;
            if (volume > 100) {
                volume = 100;
            }
            codec->SetOutputVolume(volume);
            GetDisplay()->ShowNotification(Lang::Strings::VOLUME + std::to_string(volume));
        });

        volume_up_button_.OnLongPress([this]() {
            GetAudioCodec()->SetOutputVolume(100);
            GetDisplay()->ShowNotification(Lang::Strings::MAX_VOLUME);
        });

        volume_down_button_.OnClick([this]() {
            auto codec = GetAudioCodec();
            auto volume = codec->output_volume() - 10;
            if (volume < 0) {
                volume = 0;
            }
            codec->SetOutputVolume(volume);
            GetDisplay()->ShowNotification(Lang::Strings::VOLUME + std::to_string(volume));
        });

        volume_down_button_.OnLongPress([this]() {
            GetAudioCodec()->SetOutputVolume(0);
            GetDisplay()->ShowNotification(Lang::Strings::MUTED);
        });
    }

    // 物联网初始化，逐步迁移到 MCP 协议
    void InitializeTools() {
        static LampController lamp(LAMP_GPIO);
    }

public:
    CompactWifiBoard() :
        boot_button_(BOOT_BUTTON_GPIO),
        touch_button_(TOUCH_BUTTON_GPIO),
        volume_up_button_(VOLUME_UP_BUTTON_GPIO),
        volume_down_button_(VOLUME_DOWN_BUTTON_GPIO) {
        InitializeDisplayI2c();
        InitializeSsd1306Display();
        InitializeButtons();
        InitializeTools();
    }

    virtual Led* GetLed() override {
        static SingleLed led(BUILTIN_LED_GPIO);
        return &led;
    }

    virtual AudioCodec* GetAudioCodec() override {
#ifdef AUDIO_I2S_METHOD_SIMPLEX
        static NoAudioCodecSimplex audio_codec(AUDIO_INPUT_SAMPLE_RATE, AUDIO_OUTPUT_SAMPLE_RATE,
            AUDIO_I2S_SPK_GPIO_BCLK, AUDIO_I2S_SPK_GPIO_LRCK, AUDIO_I2S_SPK_GPIO_DOUT, AUDIO_I2S_MIC_GPIO_SCK, AUDIO_I2S_MIC_GPIO_WS, AUDIO_I2S_MIC_GPIO_DIN);
#else
        static NoAudioCodecDuplex audio_codec(AUDIO_INPUT_SAMPLE_RATE, AUDIO_OUTPUT_SAMPLE_RATE,
            AUDIO_I2S_GPIO_BCLK, AUDIO_I2S_GPIO_WS, AUDIO_I2S_GPIO_DOUT, AUDIO_I2S_GPIO_DIN);
#endif
        return &audio_codec;
    }

    virtual Display* GetDisplay() override {
        return display_;
    }
};

DECLARE_BOARD(CompactWifiBoard);
