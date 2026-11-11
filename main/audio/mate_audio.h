#ifndef MATE_AUDIO_H
#define MATE_AUDIO_H

// Mate (F3): audio helpers for the wake word work.
// - MateHighPass: 2nd-order high-pass filter, removes rumble and DC drift.
// - MateLevelMeter: measures the level of a 16-bit signal and writes one line to the
//   serial log per interval, for the whole signal and for the band above 100 Hz.
// The meter never modifies the audio.

#include <cmath>
#include <cstddef>
#include <cstdint>

#include <esp_log.h>
#include <esp_timer.h>

#define MATE_DIAG_TAG "MateDiag"

// Butterworth high-pass biquad (direct form I, single precision).
class MateHighPass {
public:
    explicit MateHighPass(float cutoff_hz = 100.0f, float sample_rate_hz = 16000.0f) {
        const float w0 = 2.0f * 3.14159265f * cutoff_hz / sample_rate_hz;
        const float cos_w0 = std::cos(w0);
        const float alpha = std::sin(w0) / (2.0f * 0.70710678f);
        const float a0 = 1.0f + alpha;
        b0_ = (1.0f + cos_w0) / 2.0f / a0;
        b1_ = -(1.0f + cos_w0) / a0;
        b2_ = b0_;
        a1_ = -2.0f * cos_w0 / a0;
        a2_ = (1.0f - alpha) / a0;
    }

    inline float Process(float x) {
        const float y = b0_ * x + b1_ * x1_ + b2_ * x2_ - a1_ * y1_ - a2_ * y2_;
        x2_ = x1_;
        x1_ = x;
        y2_ = y1_;
        y1_ = y;
        return y;
    }

    // Filters `samples` values from `in` to `out` (may be the same buffer), applies
    // `gain` and saturates to 16 bits. Returns how many samples saturated.
    size_t Process(const int16_t* in, int16_t* out, size_t samples, float gain = 1.0f) {
        size_t clipped = 0;
        for (size_t i = 0; i < samples; ++i) {
            float y = Process(static_cast<float>(in[i])) * gain;
            if (y > 32767.0f) {
                y = 32767.0f;
                ++clipped;
            } else if (y < -32767.0f) {
                y = -32767.0f;
                ++clipped;
            }
            out[i] = static_cast<int16_t>(std::lrintf(y));
        }
        return clipped;
    }

private:
    float b0_, b1_, b2_, a1_, a2_;
    float x1_ = 0, x2_ = 0, y1_ = 0, y2_ = 0;
};

class MateLevelMeter {
public:
    explicit MateLevelMeter(const char* name, int64_t interval_us = 1000000)
        : name_(name), interval_us_(interval_us) {}

    // Accumulates samples. Returns true when it closed a window and wrote the line.
    bool Add(const int16_t* data, size_t samples) {
        if (data == nullptr || samples == 0) {
            return false;
        }
        for (size_t i = 0; i < samples; ++i) {
            const int32_t value = data[i];
            const int32_t magnitude = value < 0 ? -value : value;
            sum_ += value;
            sum_sq_ += static_cast<int64_t>(value) * value;
            if (magnitude > peak_) {
                peak_ = magnitude;
            }
            if (magnitude >= 32700) {
                ++clipped_;
            }
            const float voice = high_pass_.Process(static_cast<float>(value));
            const float voice_magnitude = voice < 0 ? -voice : voice;
            voice_sum_sq_ += voice * voice;
            if (voice_magnitude > voice_peak_) {
                voice_peak_ = voice_magnitude;
            }
        }
        count_ += samples;

        const int64_t now = esp_timer_get_time();
        if (window_start_us_ == 0) {
            window_start_us_ = now;
        }
        if (now - window_start_us_ < interval_us_) {
            return false;
        }

        // Integers only in the printf: this runs in tasks with a small stack.
        const float mean = static_cast<float>(sum_) / count_;
        float variance = static_cast<float>(sum_sq_) / count_ - mean * mean;
        if (variance < 0) {
            variance = 0;
        }
        ESP_LOGI(MATE_DIAG_TAG,
                 "%s: total pico=%d rms=%d dBFS | voz(>100Hz) pico=%d rms=%d dBFS | dc=%d "
                 "saturadas=%u",
                 name_, ToDbfs(static_cast<float>(peak_)), ToDbfs(std::sqrt(variance)),
                 ToDbfs(voice_peak_), ToDbfs(std::sqrt(voice_sum_sq_ / count_)),
                 static_cast<int>(mean), static_cast<unsigned>(clipped_));

        sum_ = 0;
        sum_sq_ = 0;
        peak_ = 0;
        clipped_ = 0;
        count_ = 0;
        voice_sum_sq_ = 0;
        voice_peak_ = 0;
        window_start_us_ = now;
        return true;
    }

private:
    static int ToDbfs(float amplitude) {
        if (amplitude < 1.0f) {
            return -96;
        }
        return static_cast<int>(std::lround(20.0f * std::log10(amplitude / 32768.0f)));
    }

    const char* name_;
    int64_t interval_us_;
    int64_t window_start_us_ = 0;
    int64_t sum_ = 0;
    int64_t sum_sq_ = 0;
    int32_t peak_ = 0;
    uint32_t clipped_ = 0;
    uint32_t count_ = 0;
    MateHighPass high_pass_;
    float voice_sum_sq_ = 0;
    float voice_peak_ = 0;
};

#endif  // MATE_AUDIO_H
