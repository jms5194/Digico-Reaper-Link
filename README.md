# Digico-Reaper-Link

This is a small GUI based helper application designed to help with using Digico's Copy Audio function with a Reaper DAW used for recording. 

Here's what it does:

In recording mode, if Reaper is actively recording, every time a cue is taken on the console, a marker is dropped into the Reaper. The name of the marker is labeled by the cue number plus the cue name. 

In playback tracking mode, if Reaper is not actively playing, and the console recalls a cue, Reaper will jump the cursor to position of the first marker that exists that matches the cue number/name that was just recalled. If Reaper is playing, Reaper will not react to cue recalls on the desk. 

In playback no tracking mode, Reaper will not do anything in response to cue recalls on the desk. 

How the software works:



