#ifndef MATE_DIAG_H
#define MATE_DIAG_H

// Mate (F3): diagnóstico temporal de audio. Se activa con CONFIG_MATE_AUDIO_DIAG.
// Mide el nivel de una señal de 16 bits y escribe una línea en el registro serie
// cada cierto intervalo. No modifica el audio.

#include <cmath>
#include <cstddef>
#include <cstdint>

#include <esp_log.h>
#include <esp_timer.h>

#define MATE_DIAG_TAG "MateDiag"

class MateLevelMeter {
public:
    explicit MateLevelMeter(const char* name, int64_t interval_us = 2000000)
        : name_(name), interval_us_(interval_us) {}

    // Acumula muestras. Devuelve true cuando cerró una ventana y escribió la línea.
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
        }
        count_ += samples;

        const int64_t now = esp_timer_get_time();
        if (window_start_us_ == 0) {
            window_start_us_ = now;
        }
        if (now - window_start_us_ < interval_us_) {
            return false;
        }

        // Solo enteros en el printf: esta función corre en tareas con poca pila.
        const float mean = static_cast<float>(sum_) / count_;
        float variance = static_cast<float>(sum_sq_) / count_ - mean * mean;
        if (variance < 0) {
            variance = 0;
        }
        ESP_LOGI(MATE_DIAG_TAG, "%s: pico=%d (%d dBFS) rms=%d dBFS dc=%d saturadas=%u muestras=%u",
                 name_, static_cast<int>(peak_), ToDbfs(static_cast<float>(peak_)),
                 ToDbfs(std::sqrt(variance)), static_cast<int>(mean),
                 static_cast<unsigned>(clipped_), static_cast<unsigned>(count_));

        sum_ = 0;
        sum_sq_ = 0;
        peak_ = 0;
        clipped_ = 0;
        count_ = 0;
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
};

#endif  // MATE_DIAG_H
