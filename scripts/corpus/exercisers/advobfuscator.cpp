#include "corpus_export.h"
#ifdef ADV_LEGACY
#include "MetaString.h"
#define ADV_TEXT(s) OBFUSCATED(s)
#else
#include <advobfuscator/string.h>
using namespace andrivet::advobfuscator;
#define ADV_TEXT(s) s##_obf
#endif

static unsigned consume(const char* text, unsigned state) {
    for (; *text; ++text) state = state * 33u ^ static_cast<unsigned char>(*text);
    return state;
}

CORPUS_EXPORT unsigned exercise(unsigned state) {
    state = consume(ADV_TEXT("corpus_alpha_01"), state);
    state = consume(ADV_TEXT("corpus_bravo_payload_02"), state);
    state = consume(ADV_TEXT("corpus_charlie_marker_003"), state);
    state = consume(ADV_TEXT("corpus_delta_input_string_0004"), state);
    state = consume(ADV_TEXT("corpus_echo_test_05"), state);
    state = consume(ADV_TEXT("corpus_foxtrot_example_000006"), state);
    state = consume(ADV_TEXT("corpus_golf_07"), state);
    state = consume(ADV_TEXT("corpus_hotel_text_0008"), state);
    state = consume(ADV_TEXT("corpus_india_literal_009"), state);
    state = consume(ADV_TEXT("corpus_juliet_sequence_000010"), state);
    state = consume(ADV_TEXT("corpus_kilo_case_11"), state);
    state = consume(ADV_TEXT("corpus_lima_longer_literal_000012"), state);
    state = consume(ADV_TEXT("corpus_mike_input_013"), state);
    state = consume(ADV_TEXT("corpus_november_sentinel_0014"), state);
    state = consume(ADV_TEXT("corpus_oscar_015"), state);
    state = consume(ADV_TEXT("corpus_papa_encoded_example_0016"), state);
    return state;
}
