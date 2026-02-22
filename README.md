# RealTimeAudioRecorder - Readme 
 ______     ______     ______     __            ______   __     __    __     ______                                                                           
/\  == \   /\  ___\   /\  __ \   /\ \          /\__  _\ /\ \   /\ "-./  \   /\  ___\                                                                          
\ \  __<   \ \  __\   \ \  __ \  \ \ \____     \/_/\ \/ \ \ \  \ \ \-./\ \  \ \  __\                                                                          
 \ \_\ \_\  \ \_____\  \ \_\ \_\  \ \_____\       \ \_\  \ \_\  \ \_\ \ \_\  \ \_____\                                                                        
  \/_/ /_/   \/_____/   \/_/\/_/   \/_____/        \/_/   \/_/   \/_/  \/_/   \/_____/                                                                        
                                                                                                                                                              
                   ______     __  __     _____     __     ______        ______     ______     ______     ______     ______     _____     ______     ______    
                  /\  __ \   /\ \/\ \   /\  __-.  /\ \   /\  __ \      /\  == \   /\  ___\   /\  ___\   /\  __ \   /\  == \   /\  __-.  /\  ___\   /\  == \   
                  \ \  __ \  \ \ \_\ \  \ \ \/\ \ \ \ \  \ \ \/\ \     \ \  __<   \ \  __\   \ \ \____  \ \ \/\ \  \ \  __<   \ \ \/\ \ \ \  __\   \ \  __<   
                   \ \_\ \_\  \ \_____\  \ \____-  \ \_\  \ \_____\     \ \_\ \_\  \ \_____\  \ \_____\  \ \_____\  \ \_\ \_\  \ \____-  \ \_____\  \ \_\ \_\ 
                    \/_/\/_/   \/_____/   \/____/   \/_/   \/_____/      \/_/ /_/   \/_____/   \/_____/   \/_____/   \/_/ /_/   \/____/   \/_____/   \/_/ /_/ 
                                                                                                                                                              

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