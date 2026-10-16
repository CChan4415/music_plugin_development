// juce_stub.h —— 仅用于 Wiki 代码片段的语法验证
// 模拟真实 JUCE 的**签名**（不是实现），让 clang++ -fsyntax-only 能检查 Wiki 里的代码。
// ⚠️ 这不是 JUCE，不要拿去编译插件。
#pragma once

#include <atomic>
#include <cstdint>
#include <cstddef>
#include <cmath>
#include <cstring>
#include <string>
#include <vector>
#include <memory>
#include <functional>
#include <algorithm>

namespace juce
{
    // ---------------- 基本类型 ----------------
    using int64 = long long;
    using uint32 = unsigned int;

    template <typename T> struct Rect
    {
        T x = 0, y = 0, w = 0, h = 0;
        Rect() = default;
        Rect (T x_, T y_, T w_, T h_) : x(x_), y(y_), w(w_), h(h_) {}
        Rect reduced (T) const { return *this; }
        Rect removeFromTop (T) { return *this; }
        Rect removeFromBottom (T) { return *this; }
        Rect removeFromLeft (T) { return *this; }
        Rect removeFromRight (T) { return *this; }
        T getWidth()  const { return w; }
        T getHeight() const { return h; }
    };

    // ---------------- 断言 / 调试 ----------------
    inline void jassert_impl (bool) {}
    #define jassert(x) juce::jassert_impl (x)
    #define jassertfalse juce::jassert_impl (false)

    // ---------------- ScopedNoDenormals ----------------
    struct ScopedNoDenormals { ScopedNoDenormals() noexcept = default; };

    // ---------------- String ----------------
    class String
    {
    public:
        String() = default;
        String (const char*) {}
        String (const std::string&) {}
        const char* toRawUTF8() const { return ""; }
        String& operator+= (const String&) { return *this; }
    };

    // ---------------- MemoryBlock ----------------
    class MemoryBlock
    {
    public:
        MemoryBlock() = default;
        MemoryBlock (const void*, std::size_t) {}
        void* getData() noexcept { return nullptr; }
        const void* getData() const noexcept { return nullptr; }
        std::size_t getSize() const noexcept { return 0; }
        void setSize (std::size_t, bool = false) {}
        void append (const void*, std::size_t) {}
        void reset() {}
        String toBase64Encoding() const { return {}; }
        bool fromBase64Encoding (const String&) { return true; }
    };

    // ---------------- var / ValueTree / XmlElement ----------------
    class var
    {
    public:
        var() = default;
        var (int) {}
        var (double) {}
        var (bool) {}
        var (const char*) {}
        var (const String&) {}
    };

    class ValueTree
    {
    public:
        ValueTree() = default;
        ValueTree (const String&) {}
        ValueTree createCopy() const { return {}; }
        void setProperty (const String&, const var&, void* = nullptr) {}
        var getProperty (const String&, const var& = {}) const { return {}; }
        ValueTree getChildWithName (const String&) const { return {}; }
        int getNumChildren() const { return 0; }
        ValueTree getChild (int) const { return {}; }
        void appendChild (const ValueTree&, void* = nullptr) {}
        bool isValid() const { return true; }
        String getType() const { return {}; }
    };

    class XmlElement
    {
    public:
        XmlElement (const String&) {}
        XmlElement (const char*) = delete;
        XmlElement (int) {}
        static XmlElement* createFromText (const String&) { return nullptr; }
        String toString() const { return {}; }
        void writeTo (MemoryBlock&, const void* = nullptr) const {}
        void addChildElement (XmlElement*) {}
        XmlElement* createNewChildElement (const String&) { return nullptr; }
        void setAttribute (const String&, const var&) {}
        var getStringAttribute (const String&, const String& = {}) const { return {}; }
        int getIntAttribute (const String&, int = 0) const { return 0; }
        double getDoubleAttribute (const String&, double = 0.0) const { return 0.0; }
        bool getBoolAttribute (const String&, bool = false) const { return false; }
        bool hasAttribute (const String&) const { return false; }
        XmlElement* getFirstChildElement() const { return nullptr; }
        String getTagName() const { return {}; }
        static XmlElement* parseXML (const String&) { return nullptr; }
    };

    class File
    {
    public:
        File() = default;
        File (const String&) {}
        bool existsAsFile() const { return false; }
        bool replaceWithText (const String&) { return true; }
        String loadFileAsString() const { return {}; }
    };

    // ---------------- AudioBuffer ----------------
    template <typename Type>
    class AudioBuffer
    {
    public:
        AudioBuffer() = default;
        AudioBuffer (int numChannels, int numSamples) { setSize (numChannels, numSamples); }

        void setSize (int newNumChannels, int newNumSamples,
                      bool keepExistingContent = false, bool = false, bool = false) {}
        int getNumChannels() const noexcept { return numChannels; }
        int getNumSamples() const noexcept { return numSamples; }
        bool hasBeenCleared() const noexcept { return false; }

        Type* getWritePointer (int channel) noexcept { return data; }
        const Type* getReadPointer (int channel) const noexcept { return data; }
        Type** getArrayOfWritePointers() noexcept { return ptrs; }
        const Type* const* getArrayOfReadPointers() const noexcept { return ptrs; }

        void clear() noexcept {}
        void clear (int startSample, int numSamples) noexcept {}
        void clear (int channel, int startSample, int numSamples) noexcept {}

        void applyGain (Type gain) noexcept {}
        void applyGain (int channel, int startSample, int numSamples, Type gain) noexcept {}
        void applyGainRamp (int channel, int startSample, int numSamples, Type s, Type e) noexcept {}

        void addFrom (int destChannel, int destStartSample, const AudioBuffer& source,
                      int sourceChannel, int sourceStartSample, int numSamples, Type gain = Type (1)) noexcept {}
        void copyFrom (int destChannel, int destStartSample, const AudioBuffer& source,
                       int sourceChannel, int sourceStartSample, int numSamples) noexcept {}
        void copyFrom (int destChannel, int destStartSample, const Type* source, int numSamples) noexcept {}

        Type getSample (int channel, int index) const noexcept { return Type (0); }
        void setSample (int channel, int index, Type v) noexcept {}
        Type getMagnitude (int startSample, int numSamples) const noexcept { return Type (0); }

        Type* data = nullptr;
        Type** ptrs = nullptr;
        int numChannels = 0, numSamples = 0;
    };

    // ---------------- MidiBuffer ----------------
    class MidiMessage
    {
    public:
        static MidiMessage noteOn (int, float, float) { return {}; }
        static MidiMessage noteOff (int, float, float) { return {}; }
        int getNoteNumber() const { return 0; }
        float getFloatVelocity() const { return 0.0f; }
        bool isNoteOn (bool = true) const { return false; }
        bool isNoteOff (bool = true) const { return false; }
        bool isAllNotesOff() const { return false; }
        bool isController() const { return false; }
        int getControllerNumber() const { return 0; }
        int getControllerValue() const { return 0; }
        bool isPitchWheel() const { return false; }
        int getPitchWheelValue() const { return 0; }
    };

    class MidiBuffer
    {
    public:
        struct Iterator
        {
            const std::uint8_t* data = nullptr;
            bool operator!= (const Iterator&) const { return false; }
            void operator++() {}
            const std::uint8_t* getMessage() const { return data; }
            int getSamplePosition() const { return 0; }
            int getMessageSize() const { return 0; }
        };
        Iterator begin() const { return {}; }
        Iterator end() const { return {}; }
        void addEvent (const MidiMessage&, int) {}
        void clear() {}
        int getNumEvents() const { return 0; }
    };

    // ---------------- AbstractFifo ----------------
    class AbstractFifo
    {
    public:
        explicit AbstractFifo (int capacity) noexcept : size (capacity) {}

        int getTotalSize() const noexcept { return size; }
        int getFreeSpace() const noexcept { return size - ready.load(); }
        int getNumReady() const noexcept { return ready.load(); }

        void reset() noexcept { ready.store (0); }

        void prepareToWrite (int numToWrite, int& start1, int& size1,
                             int& start2, int& size2) noexcept {}
        int writeFinished (int numWritten) noexcept { return 0; }
        int write (int numToWrite) noexcept { return 0; }

        void prepareToRead (int numWanted, int& start1, int& size1,
                            int& start2, int& size2) noexcept {}
        int readFinished (int numRead) noexcept { return 0; }
        int read (int numToRead) noexcept { return 0; }

        // 简化：为验证而存在的 ScopedWrite / ScopedRead
        struct ScopedWrite
        {
            ScopedWrite (AbstractFifo& f, int n) : fifo (f) {}
            int getNumSegments() const { return 0; }
            int getStart (int) const { return 0; }
            int getSize (int) const { return 0; }
            void finished (int) {}
        private:
            AbstractFifo& fifo;
        };
        struct ScopedRead
        {
            ScopedRead (AbstractFifo& f, int n) : fifo (f) {}
            int getNumSegments() const { return 0; }
            int getStart (int) const { return 0; }
            int getSize (int) const { return 0; }
            void finished (int) {}
        private:
            AbstractFifo& fifo;
        };

    private:
        int size = 0;
        std::atomic<int> ready { 0 };
    };

    // ---------------- 参数系统 ----------------
    class AudioProcessorParameter
    {
    public:
        virtual ~AudioProcessorParameter() = default;
        virtual float getValue() const { return 0.0f; }
        virtual void setValue (float) {}
        virtual float getDefaultValue() const { return 0.0f; }
        virtual String getName (int) const { return {}; }
        virtual String getText (float, int) const { return {}; }
        virtual int getNumSteps() const { return 0; }
        virtual bool isDiscrete() const { return false; }
        virtual bool isBoolean() const { return false; }
        virtual bool isMetaParameter() const { return false; }
        virtual String getParameterID() const { return {}; }
        virtual void beginChangeGesture() {}
        virtual void endChangeGesture() {}
        void setValueNotifyingHost (float) {}
        float getValueUnnormalised() const { return 0.0f; }
        void setValueNotifyingHost (float, bool) {}
    };

    class AudioParameterFloat : public AudioProcessorParameter
    {
    public:
        struct Attributes
        {
            Attributes() = default;
            Attributes (float min, float max, float def) : minValue (min), maxValue (max), defaultValue (def) {}
            Attributes (float min, float max, float def, float skew) : minValue (min), maxValue (max), defaultValue (def), skewMidpoint (skew) {}
            Attributes (const String&, float min, float max, float def) : minValue (min), maxValue (max), defaultValue (def) {}
            float minValue = 0.0f, maxValue = 1.0f, defaultValue = 0.0f, skewMidpoint = 1.0f;
        };
        AudioParameterFloat (const String& id, const String& name, Attributes a) {}
        AudioParameterFloat (const String& id, const String& name, float min, float max, float def) {}
        AudioParameterFloat (const String& id, const String& name, float min, float max, float def, float skew) {}
        operator float() const { return 0.0f; }
        float get() const { return 0.0f; }
        AudioParameterFloat& operator= (float) { return *this; }
        float getValue() const override { return 0.0f; }
    };

    class AudioParameterChoice : public AudioProcessorParameter
    {
    public:
        AudioParameterChoice (const String& id, const String& name,
                              const std::vector<String>& choices, int def) {}
        operator int() const { return 0; }
        int getIndex() const { return 0; }
    };

    class AudioParameterBool : public AudioProcessorParameter
    {
    public:
        AudioParameterBool (const String& id, const String& name, bool def) {}
        operator bool() const { return false; }
    };

    // ---------------- UI（最小集，供 Wiki 代码语法检查）----------------
    struct Graphics
    {
        void fillAll() {}
        void setColour (int, int) {}
        void drawText (const String&, int, int, int, int) {}
    };
    struct Colour { Colour() = default; Colour (unsigned int) {} };

    class Component
    {
    public:
        Component() = default;
        virtual ~Component() = default;
        virtual void paint (Graphics&) {}
        virtual void resized() {}
        virtual void mouseDown (const void*) {}
        void setSize (int, int) {}
        void addAndMakeVisible (Component*) {}
        void addAndMakeVisible (Component&) {}
        int  getWidth()  const { return 0; }
        int  getHeight() const { return 0; }
        Rect<int> getLocalBounds() const { return {0,0,0,0}; }
        void setBounds (int, int, int, int) {}
        void setBounds (const Rect<int>&) {}          // 真实 JUCE 有 Rect 重载
    };

    class Slider : public Component
    {
    public:
        enum Style { LinearHorizontal, LinearVertical, Rotary, RotaryHorizontalVerticalDrag };
        enum TextEntryBoxPosition { NoTextBox, TextBoxLeft, TextBoxRight, TextBoxAbove, TextBoxBelow };
        Slider() = default;
        Slider (Style) {}
        void setRange (double, double, double = 0.0) {}
        void setValue (double, int = 0) {}
        double getValue() const { return 0.0; }
        void setSliderStyle (Style) {}
        void setTextBoxStyle (TextEntryBoxPosition, bool, int, int) {}
        void setSkewFactorFromMidPoint (double) {}
        void setTextValueSuffix (const String&) {}
        void onValueChange (std::function<void()>) {}
        void setNumDecimalPlacesToDisplay (int) {}
    };

    class Label : public Component
    {
    public:
        Label() = default;
        Label (const String&, const String&) {}
        void setText (const String&, int = 0) {}
        void setJustificationType (int) {}
        void attachToComponent (Component*, bool) {}
    };

    class Button : public Component
    {
    public:
        Button() = default;
        void setButtonText (const String&) {}
        void onClick (std::function<void()>) {}
    };

    class TextButton : public Button
    {
    public:
        TextButton() = default;
        TextButton (const String&) {}
    };

    class ComboBox : public Component
    {
    public:
        ComboBox() = default;
        void addItem (const String&, int) {}
        void setSelectedId (int, int = 0) {}
        int  getSelectedId() const { return 0; }
        void onChange (std::function<void()>) {}
    };

    class Timer
    {
    public:
        virtual ~Timer() = default;
        virtual void timerCallback() {}
        void startTimerHz (int) {}
        void stopTimer() {}
    };

    class AudioProcessorValueTreeState;

    // ---------------- 声道集合 ----------------
    class AudioChannelSet
    {
    public:
        static AudioChannelSet stereo()   { return {}; }
        static AudioChannelSet mono()     { return {}; }
        static AudioChannelSet disabled() { return {}; }
        bool operator== (const AudioChannelSet&) const { return true; }
        bool operator!= (const AudioChannelSet&) const { return false; }
    };

    // ---------------- 参数平滑 ----------------
    template <typename T>
    class SmoothedValue
    {
    public:
        void reset (double, double) {}
        void setTargetValue (T) {}
        T getNextValue() { return T{}; }
        T getCurrentValue() const { return T{}; }
        void setCurrentAndTargetValue (T) {}
    };

    class AudioProcessor;      // 前置声明（AudioProcessorEditor 的构造函数要用）

    // ⚠️ 真实 JUCE 里 AudioProcessorEditor 是 juce 命名空间级的类
    class AudioProcessorEditor : public Component
    {
    public:
        AudioProcessorEditor() = default;
        explicit AudioProcessorEditor (AudioProcessor*) {}
    };

    class AudioProcessor
    {
    public:
        struct BusesProperties
        {
            BusesProperties() = default;
            BusesProperties withInput  (const String&, const AudioChannelSet&, bool = true) const { return *this; }
            BusesProperties withOutput (const String&, const AudioChannelSet&, bool = true) const { return *this; }
        };

        AudioProcessor() = default;
        explicit AudioProcessor (const BusesProperties&) {}
        virtual ~AudioProcessor() = default;

        virtual void prepareToPlay (double sampleRate, int samplesPerBlock) {}
        virtual void releaseResources() {}
        virtual void processBlock (AudioBuffer<float>& buffer, MidiBuffer& midi) = 0;
        virtual void processBlockBypassed (AudioBuffer<float>& buffer, MidiBuffer& midi) {}

        void addParameter (AudioProcessorParameter*) {}

        virtual void getStateInformation (MemoryBlock& destData) {}
        virtual void setStateInformation (const void* data, int sizeInBytes) {}

        virtual const String getName() const { return {}; }
        virtual double getSampleRate() const { return 48000.0; }
        virtual int getBlockSize() const { return 512; }
        virtual int getTotalNumInputChannels() const { return 2; }
        virtual int getTotalNumOutputChannels() const { return 2; }
        virtual bool isBusesLayoutSupported (const BusesProperties&) const { return true; }
        virtual bool acceptsMidi() const { return false; }
        virtual bool producesMidi() const { return false; }
        virtual bool isMidiEffect() const { return false; }
        virtual double getTailLengthSeconds() const { return 0.0; }
        virtual AudioProcessorEditor* createEditor() { return nullptr; }
        virtual bool hasEditor() const { return false; }
        virtual int getNumPrograms() { return 1; }
        virtual int getCurrentProgram() { return 0; }
        virtual void setCurrentProgram (int) {}
        virtual const String getProgramName (int) { return {}; }
        virtual void changeProgramName (int, const String&) {}
        virtual bool supportsDoublePrecisionProcessing() const { return false; }
        virtual void processBlock (AudioBuffer<double>&, MidiBuffer&) {}

        void setLatencySamples (int newLatency) { latencySamples = newLatency; }
        int getLatencySamples() const { return latencySamples; }
        void setRateAndBufferSizeDetails (double, int) {}
        void updateHostDisplay() {}
        void suspendProcessing (bool) {}
        bool isSuspended() const { return false; }

    protected:
        class BusesLayout {};
        int latencySamples = 0;
    };

    class AudioProcessorValueTreeState
    {
    public:
        struct RangedAudioParameter : AudioProcessorParameter {};
        struct ParameterAttachment
        {
            ParameterAttachment (RangedAudioParameter&, std::function<void (float)>, void* = nullptr) {}
            void sendInitialUpdate() {}
            void setValueAsCompleteGesture (float) {}
        };

        AudioProcessorValueTreeState (AudioProcessor&, void* = nullptr) {}
        AudioProcessorParameter* getParameter (const String&) const { return nullptr; }
        float getRawParameterValue (const String&) const { return 0.0f; }
        std::atomic<float>* getRawParameterValue (const char*) const { return nullptr; }
        ValueTree state;
        ValueTree copyState() const { return {}; }
        void replaceState (const ValueTree&) {}
        void addParameterListener (const String&, void*) {}
        bool setStateFromXml (const XmlElement&) { return true; }
        void createAndAddParameter (std::unique_ptr<AudioProcessorParameter>) {}
    };

    // ---------------- dsp ----------------
    namespace dsp
    {
        template <typename T, int N>
        struct SIMDRegister
        {
            SIMDRegister() = default;
            SIMDRegister (T v) { for (int i = 0; i < N; ++i) v_[i] = v; }
            static constexpr int size() { return N; }
            static SIMDRegister expand (T v) { return SIMDRegister (v); }
            static void clear (SIMDRegister& r) { r = SIMDRegister (T (0)); }
            T& operator[] (int i) { return v_[i]; }
            const T& operator[] (int i) const { return v_[i]; }
            SIMDRegister operator+ (const SIMDRegister& o) const { return *this; }
            SIMDRegister operator- (const SIMDRegister& o) const { return *this; }
            SIMDRegister operator* (const SIMDRegister& o) const { return *this; }
            SIMDRegister operator/ (const SIMDRegister& o) const { return *this; }
            SIMDRegister& operator+= (const SIMDRegister&) { return *this; }
            SIMDRegister& operator*= (const SIMDRegister&) { return *this; }
            static SIMDRegister multiplyAdd (const SIMDRegister& a, const SIMDRegister& b, const SIMDRegister& c) { return c; }
            static SIMDRegister select (const SIMDRegister&, const SIMDRegister& a, const SIMDRegister&) { return a; }
            static SIMDRegister min (const SIMDRegister& a, const SIMDRegister&) { return a; }
            static SIMDRegister max (const SIMDRegister& a, const SIMDRegister&) { return a; }
            static SIMDRegister abs (const SIMDRegister& a) { return a; }
            static SIMDRegister clamp (const SIMDRegister& a, const SIMDRegister&, const SIMDRegister&) { return a; }
            T v_[N] {};
        };

        template <typename T>
        struct SIMDFloat : SIMDRegister<T, 4> {};

        template <typename T>
        struct AudioBlock
        {
            T* const* channels = nullptr;
            int numChannels = 0, numSamples = 0;
            static AudioBlock fromChannelPointer (T* const*, int, int) { return {}; }
            int getNumChannels() const { return numChannels; }
            int getNumSamples() const { return numSamples; }
            T* getChannelPointer (int) const { return nullptr; }
            AudioBlock getSubBlock (int, int) const { return *this; }
        };

        template <typename T>
        class Oversampling
        {
        public:
            enum FilterType { filterHalfBandPolyphaseIIR, filterHalfBandFIREquiripple };
            Oversampling (size_t numChannels, size_t factor, FilterType type, bool useIntegerLatency = false) {}
            void initProcessing (size_t maximumNumberOfSamplesBeforeOversampling) {}
            void reset() {}
            double getLatencyInSamples() const { return 0.0; }
            int getOversamplingFactor() const { return 2; }
            AudioBlock<T> processSamplesUp (const AudioBlock<T>& inputBlock) { return {}; }
            void processSamplesDown (AudioBlock<T>& outputBlock) {}
        };

        template <typename T>
        class DryWetMixer
        {
        public:
            DryWetMixer() = default;
            void prepare (double sampleRate, int maximumBlockSize, int numChannels) {}
            void pushDrySamples (const AudioBlock<T>&) {}
            void mixWet (AudioBlock<T>&, AudioBlock<T>&) {}
            void setWetRatio (T) {}
            void setDryRatio (T) {}
        };
    }

    // ---------------- 其他 ----------------
    class AudioPlayHead
    {
    public:
        struct CurrentPositionInfo
        {
            double bpm = 120.0, ppqPosition = 0.0, timeInSeconds = 0.0;
            int timeSigNumerator = 4, timeSigDenominator = 4;
            bool isPlaying = false;
        };
        virtual ~AudioPlayHead() = default;
        virtual bool getCurrentPosition (CurrentPositionInfo&) { return false; }
    };
}
