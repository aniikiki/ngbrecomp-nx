#pragma once
#include <stddef.h>
#include <stdint.h>
// Single guest producer for each stream; device worker consumes PCM only.
int ngb_audio_device_open(void);
void ngb_audio_device_close(void);
// A null source queues the same duration of silence.
void ngb_pcm_submit(unsigned movie,const int16_t *stereo,unsigned frames);
void ngb_pcm_flush(unsigned movie);
void ngb_pcm_render(int16_t *stereo,unsigned frames);
