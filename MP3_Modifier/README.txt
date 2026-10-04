There are 2 python programs in this folder - main.py and overlay_audio.py.
Both serve different functions.


1) Run the program as follows for trimming an mp3 file called song.mp3 according to the given timestamps.

python main.py song.mp3 1:20 3:22

2) For overlaying one overlay mp3 over the main mp3 file run the command as follows. The --at indicates which parts of the main file the overlay should be played at.

python overlap_audio.py main.mp3 overlay.mp3 --at 0:35 --at 1:48 --at 2:59