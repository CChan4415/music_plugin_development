#include "juce_stub.h"
struct P : juce::AudioProcessor {
    void processBlock (juce::AudioBuffer<float>& b, juce::MidiBuffer& m) override {}
};
int main(){ return 0; }
