---
title: JUCE 8.0.4 官方插件编辑器示例
type: source
domain: ui
status: solid
confidence: high
tags: [reference, recipe]
source_type: official-example
url: https://github.com/juce-framework/JUCE/blob/8.0.4/examples/CMake/AudioPlugin/PluginEditor.cpp
author: Raw Material Software Limited (JUCE)
year: 2025
note: 官方插件编辑器（最简）
created: 2026-10-16
updated: 2026-10-16
---

> [!important] 官方示例原文（只读真相锚点）
> 来源：JUCE 8.0.4。引用它的页面见 [[JUCE Component 体系]]、[[JUCE 的 Slider 与旋钮]]。

---

#include "PluginProcessor.h"
#include "PluginEditor.h"

//==============================================================================
AudioPluginAudioProcessorEditor::AudioPluginAudioProcessorEditor (AudioPluginAudioProcessor& p)
    : AudioProcessorEditor (&p), processorRef (p)
{
    juce::ignoreUnused (processorRef);
    // Make sure that before the constructor has finished, you've set the
    // editor's size to whatever you need it to be.
    setSize (400, 300);
}

AudioPluginAudioProcessorEditor::~AudioPluginAudioProcessorEditor()
{
}

//==============================================================================
void AudioPluginAudioProcessorEditor::paint (juce::Graphics& g)
{
    // (Our component is opaque, so we must completely fill the background with a solid colour)
    g.fillAll (getLookAndFeel().findColour (juce::ResizableWindow::backgroundColourId));

    g.setColour (juce::Colours::white);
    g.setFont (15.0f);
    g.drawFittedText ("Hello World!", getLocalBounds(), juce::Justification::centred, 1);
}

void AudioPluginAudioProcessorEditor::resized()
{
    // This is generally where you'll want to lay out the positions of any
    // subcomponents in your editor..
}
