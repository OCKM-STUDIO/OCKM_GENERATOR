#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// All Pd/Lua activity is owned by one worker. The hardware callback only reads
// a preallocated single-producer/single-consumer audio ring.
int ockm_open(const char *runtime_path, int sample_rate);
void ockm_close(void);
void ockm_command(const char *selector, const char *symbol, float a, float b, int count);
void ockm_float(const char *receiver, float value);
void ockm_render(float *left, float *right, uint32_t frames);
char *ockm_copy_frame(void);
char *ockm_copy_log(void);
void ockm_free(void *pointer);
uint64_t ockm_underruns(void);
int ockm_midi_input_count(void);
int ockm_midi_output_count(void);
char *ockm_midi_name(int output, int index);
void ockm_midi_select(int input_index, int output_index);
#ifdef __cplusplus
}
#endif
