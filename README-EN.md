# Sound Manager

[Guia em português](README.md)

Browse your sound library, listen to files and edit selections in a single window. Sound Manager works with files on your computer and runs offline.

## Open the app

1. Extract the downloaded package to a folder on your computer.
2. **Windows:** double-click `SoundManager.exe`.
3. **Linux:** open `SoundManager`. If execution permission is required, mark the file as executable in its properties or run `chmod +x SoundManager` in a terminal.

You do not need to install Python or FFmpeg to use the app package. If the package contains an `_internal` folder, keep it beside the program. The first launch may take a few seconds.

## Choose your language

Use **Idioma / Language** in the upper-right corner to choose **Português (BR)** or **English**. The interface changes immediately, preserving your current edits and playback.

Your choice is saved automatically and used the next time you open the app. Your file and folder names stay unchanged.

## Choose your sounds

On your first launch, click **Choose library…** and select the folder containing your audio files. You can change this folder at any time. The app does not include a sound library.

Folders appear on the left. Click one to see its sounds in the list on the right. **Up** moves to the parent folder, and **Root** returns to the library's main folder. Use **Open file…** to open a sound from another location.

Use the search fields to find files:

- **Filter folders or files…** on the left searches folder names and filenames inside them.
- **Filter files by name…** on the right searches only the files in the current folder.

Type part of a name; searches are case-insensitive. Click **×** to clear a filter or **↻** to refresh after changing files outside the app.

## Listen to a sound

Click **▶** in a file's row to listen. Click it again to pause. Double-clicking the filename also plays the sound.

The same row contains the playback time, volume, **■ Stop** and **↻ Loop** controls. Playback volume changes what you hear; it does not change the volume recorded in the file.

## Select and edit audio

1. Click **Trim** in the file's row to open the waveform.
2. Drag over the waveform to select the section you want.
3. Adjust the green handles or the **Start** and **End** fields to refine the selection.
4. Click **Play** to hear the selection. The button changes to **Pause** during playback; click it to pause and **Play** to resume.

The **yellow line on the waveform** shows the playback position. It is a visual indicator. To change the playback or paste position, click or drag the **yellow bar below the waveform**. Dragging on the waveform selects audio or adjusts the selection handles.

Use the magnifying glass buttons or the mouse wheel to zoom. The gray scrollbar moves through the zoomed waveform, and the fit button shows the entire sound again. **Close** collapses the editor in the list.

Hover over an icon to see what it does. The editing tools let you:

- **Copy:** keep the selected audio for pasting later.
- **Paste:** insert copied audio at the yellow bar position, including into another file.
- **Remove selection:** delete the selected audio and join the parts before and after it. This edits the audio without deleting the library file.
- **Undo / Redo:** reverse an edit or apply it again.
- **Select all:** select the entire audio.
- **Reverse:** play the selection backwards.
- **Volume − / +:** decrease or increase the selection's volume by the dB value shown beside the buttons.
- **Fade in / Fade out:** make the selection start softly or gradually fade away. The **Fade** field sets the effect's duration in seconds.

Copied audio remains available during the session. Copying another selection replaces the previous copy.

## Save your changes

**Save audio** writes the entire audio to **the same file that is currently open**. The app displays its path and asks for confirmation before replacing it. This button does not use the selection export folder.

**Save selection…** creates a file containing only the selected audio. Choose its name, folder and format: WAV, OGG, FLAC or MP3. Use a different name or destination to preserve the open file. WAV and FLAC avoid the lossy compression used by OGG and MP3.

Edits are kept when you switch between files during the session. **To keep them after closing the app, use Save audio and confirm.** Unsaved changes are lost when you close the app.

## Copy files to another folder

Drag a **filename** to a folder in the tree on the left or to a folder in your computer's file manager. Use Ctrl or Shift to select multiple files.

Dragging creates a copy and keeps the source file. When copying inside the app, duplicate names receive a suffix such as `(copy)` in English or `(cópia)` in Portuguese, preserving the file already at the destination. **Show file** opens the original sound's folder.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| Space | Play / pause |
| Ctrl+O | Open a file |
| Ctrl+A | Select all audio with the editor open; select files with the editor closed |
| Ctrl+C | Copy the selected audio |
| Ctrl+V | Paste at the yellow bar position |
| Ctrl+Z | Undo |
| Ctrl+Y or Ctrl+Shift+Z | Redo |
| Ctrl+S | Save the entire audio to the open file after confirmation |
| Ctrl+Shift+S | Save the selection to another file |
| Alt+↑ | Go up one folder |

In text fields, Ctrl+A continues to select the field's text.

## Preferences and formats

The app remembers your language, library, last open folder, window size and position, playback volume, loop setting and last selection export folder.

Supported input formats: **WAV, OGG, MP3, FLAC, AIFF, M4A, AAC, OPUS and WMA**.

## Troubleshooting

- **No sound:** check the volume in the file's row, your system volume and the audio output device selected on your computer.
- **A file will not open:** try another sound to check whether the problem is specific to that file. The app displays a message when it encounters damaged audio.
- **The app will not start on Linux:** make sure a graphical desktop and the required Qt system libraries are available. On Ubuntu/Debian, the usual dependencies can be installed with:

```bash
sudo apt-get install libegl1 libgl1 libopengl0 libxkbcommon-x11-0 \
  libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
  libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 libdbus-1-3 libpulse0
```
