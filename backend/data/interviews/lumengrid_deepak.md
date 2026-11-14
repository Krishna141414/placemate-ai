---
id: interview-lumengrid-deepak
doc_type: interview
title: LumenGrid Energy interview experience - Deepak S. (EEE, 2026 batch, selected)
company_id: lumengrid
---

# LumenGrid Energy interview experience - Deepak S. (EEE, 2026 batch, selected)

(Fictional sample write-up.)

## Online Assessment

Two coding problems and 20 multiple-choice questions. I used C++. The problems were to find the missing reading in a sequence of meter readings (an arithmetic progression with one gap) and to group readings by hour and report the peak hour. The MCQs covered operating systems, networking and some basic electronics such as Ohm's law and logic gates.

## Technical Interview

C++ questions: the difference between a pointer and a reference, what a memory leak is, and what happens when a vector grows. In Python: the difference between a list and a set, and how to read a large file without loading it all into memory.

The interesting question was a practical one: "A meter sends a reading every 15 minutes. The network is down for two hours. What should the meter do?" I said it should store the readings locally with timestamps, send them when the network returns, and the server should ignore duplicates. He then asked what to do if the storage on the device fills up.

There was one simple SQL query on finding the average reading per meter per day.

## Project Presentation

Ten minutes to present and ten for questions. I presented my energy monitor built with an ESP32 that publishes over MQTT. Bring a working demo or at least a video. They asked about the mistakes I made, more than about the features.

## Tips

- Remember that LumenGrid does not allow any active backlog. Two of my friends could not apply for that reason alone.
- Pick a project you built yourself for the presentation round.
