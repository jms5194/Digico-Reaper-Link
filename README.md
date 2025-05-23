# Digico-Reaper-Link

<img width="333" alt="Digico-Reaper Link GUI" src="https://github.com/user-attachments/assets/e8656c93-b73b-4da0-8a0b-833c0e9f54e9">

This is a small GUI based helper application designed to help with using Digico's Copy Audio function with a Reaper DAW used for recording. 

This Readme is for V3.3.8 and later, which is a signficant new iteration for the application. V1 is still available in releases, but the information below will not apply. 

If you just want to download the software- here's the link:

<a href="https://www.github.com/jms5194/Digico-Reaper-Link/releases/latest">Download Here!</a>

The application is available for macOS (Arm and Intel) as well as Windows. The macOS builds are signed and notarized. The Windows builds are not signed, and may be flagged by SmartScreen. Also, the Windows build may require you to build a firewall rule that allows the application through the firewall, at least my testing machine did. 

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

This will use your iPad slot on your Digico console. If you are running a dual engine console, you can connect Digico-Reaper Link to one engine and an iPad to another, but on a single engine desk, if you want to run and iPad as well as Digico-Reaper Link, you can use the repeater functionality inside of Digico-Reaper Link. In the preferences you can set up a repeater address, and if you place a iPad at that location (or other relevant OSC device), Digico-Reaper Link will repeater bi-directionally all of the OSC required for that device. 

You don't need to do any configuration in Reaper. When you open Digico-Reaper Link, if Reaper is not running, it will prompt you to open Reaper. The first time Digico-Reaper Link sees Reaper, it will write a new interface to Reaper's OSC interface list. It will then prompt you to close and reopen Reaper, to initialize the new interface. Then every open it will check that the correct interface is in place, and continue to make connections as long as it is. 

When Digico-Reaper Link is open, go to File-->Preferences, and input your consoles IP address and the ports you are using, and you should be all set!

<img width="450" alt="Digico-Reaper Perfs" src="https://github.com/user-attachments/assets/8e558378-8921-4c10-b77e-2066b84c90c0" />


Features (Updated 5/23/25):

Name Only Mode- There is now a preference to match on name of Cue/Snapshot only. If you are reordering your snapshots, and want it to jump to the marker disregarding the cue number, this preference will make it match on name only. Obviously, this assumes your cue names are unique, if they are not, it will just go to the first marker that matches the name of the cue. 

Repeater- If you want OSC to pass through this app to another device (such as an ipad)- you can now set that up in the preferences page of the app, and the app will repeat OSC to another IP address/ports. 

Heartbeat with Digico- In the UI window, the red square that says N/C will turn to green and have the type of console in it when a Digico console connection is established. This status is refreshed every 5 seconds, so you should be able to easily tell if you've lost connection with the console. 

Drop Marker Button- Useful for confirming that your connection to Reaper is sound, this will drop a marker into Reaper upon button press in the UI. 

Attempt Reconnect Button- This closes and reopens all of the connections to the OSC Clients/Servers. Useful if you have changed your network configuration or a cable has become disconnected, you can reset the connections without closing and reopening the app. 

Macros from Digico- You can now control Reaper from macros on your Digico console through Digico-Reaper Link. All you have to do is label the macros- they don't have to have any actions in them. Supported behaviors are. 

Play<br>
Stop<br>
Record (This is a safe record, it will always skip to the end of all recordings and then start recording, as well as place you into recording mode)<br>
Drop Marker<br>
Record Mode<br>
Playback Tracking Mode<br>
Playback No Track Mode<br>


You can label the macros with any of the options below and Reaper-Digico Link will detect them (any capitalization anywhere will be ignored):

Reaper,Play- Reaper Play - Play<br>
Reaper,Stop - Reaper Stop - Stop<br>
Reaper,Rec - Reaper Rec - Rec - Record<br>
Reaper,Marker - Reaper Marker - Marker<br>
Mode,Rec - Mode Rec - Mode Recording<br>
Mode,Track - Mode, Tracking - Mode Track - Mode Tracking<br>
Mode,No Track - Mode No Track - Mode No Tracking<br>


See an example in the images below:

![macro buttons](https://github.com/user-attachments/assets/b23ca08f-a874-4b6a-871b-9007d02613c6)![macros](https://github.com/user-attachments/assets/954f9f07-a841-4ba6-90ad-ab294a9e27c7)


If this software has been useful to you, consider making a donation via the github sponsors system below:

[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/jms5194)




