# Digico-Reaper-Link
<img width="211" alt="Screen Shot 2021-11-10 at 10 49 08 PM" src="https://user-images.githubusercontent.com/79057472/141206402-2f8f9612-7a2f-491a-9cb9-8ba5ffe6638e.png">


This is a small GUI based helper application designed to help with using Digico's Copy Audio function with a Reaper DAW used for recording. 

Here's what it does:

In recording mode, if Reaper is actively recording, every time a cue is taken on the console, a marker is dropped into the Reaper. The name of the marker is labeled by the cue number plus the cue name. 

In playback tracking mode, if Reaper is not actively playing, and the console recalls a cue, Reaper will jump the cursor to position of the first marker that exists that matches the cue number/name that was just recalled. If Reaper is playing, Reaper will not react to cue recalls on the desk. 

In playback no tracking mode, Reaper will not do anything in response to cue recalls on the desk. 

How the software works:

Digico-Reaper Link makes an OSC connection to the Digico console, emulating an iPad interface. It also makes an internal OSC connection to Reaper. The software acts as an OSC translation layer. 

How to set it up:

On your Digico console, configure External Control for the IP address of your Reaper computer and load the iPad command set. 
Set the ports as you desire. Your configuration on the console should look something like this:

![external control](https://user-images.githubusercontent.com/79057472/141206529-99671316-4b3b-47c3-96af-803fbd5f8889.jpg)


Then in Reaper, go to Preferences-->Control/OSC/Web. 
Add a new control interface. Device IP must be 127.0.0.1. You should not change local IP. You can set the ports as you desire. You can use the default pattern config file, but a better one is located in this github called Digico.ReaperOSC. If you want to use that one, take that file from the Github and put it in ~/Library/Application Support/Reaper/OSC, and then it should show up as an option in the pattern drop down. 

<img width="629" alt="Screen Shot 2021-11-10 at 10 53 26 PM" src="https://user-images.githubusercontent.com/79057472/141206755-fb282265-9c9e-413b-b911-3b6037ed5e01.png">

Lastly, open Digico-Reaper Link. Go to File-->Preferences, and input your consoles IP address, the IP address your computer is on on the same subnet as the console, and the ports you are using, and you should be all set!

<img width="209" alt="image" src="https://user-images.githubusercontent.com/79057472/141976598-53eafc70-84b3-40c2-9531-ebab6ae312c4.png">

