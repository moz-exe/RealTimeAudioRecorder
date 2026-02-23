# RealTimeAudioRecorder - Readme 
  ___          _   _____ _                                     
 | _ \___ __ _| | |_   _(_)_ __  ___                           
 |   / -_) _` | |   | | | | '  \/ -_)                          
 |_|_\___\__,_|_|   |_|_|_|_|_|_\___|                _         
         /_\ _  _ __| (_)___  | _ \___ __ ___ _ _ __| |___ _ _ 
        / _ \ || / _` | / _ \ |   / -_) _/ _ \ '_/ _` / -_) '_|
       /_/ \_\_,_\__,_|_\___/ |_|_\___\__\___/_| \__,_\___|_|  
                                                                    

## Presentation

This tool records the computer's audio output and exports it buffer by buffer in .wav files in real time.  
It uses the PyAudioWPatch 0.2.12.8 library which is a fork of the popular PyAudio library that allows you to use output devices in loopback mode.  
Unfortunately, this library only works for Windows.  

## How to use

Execute the script RealTimeAudioRecorder.sh  
It will check and install the required libraries and execute the programm.  

## Why

Its aim is to be integrated in a vishing detection tool which analyses calls in real time.  
It will be chained between an interface which will decide when to execute the tool and an AI vishing detection model which will analise the audio and give its result back to the interface.