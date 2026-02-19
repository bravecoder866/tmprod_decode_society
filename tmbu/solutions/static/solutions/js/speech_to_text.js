/*
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.      
*/


document.addEventListener('DOMContentLoaded', () => {
    let mediaRecorder;
    let audioChunks = [];
    let activeTextarea = null;
    let activeStatusDisplay = null;
    let mediaStream = null;
    let isRecording = false;
  
    const recordButtons = document.querySelectorAll('.record');
    const stopButtons = document.querySelectorAll('.stop');
  
    const updateButtonStates = (recording) => {
      recordButtons.forEach(button => button.disabled = recording);
      stopButtons.forEach(button => button.disabled = !recording);
      if (activeStatusDisplay) {
        activeStatusDisplay.textContent = recording ? gettext('Recording...') : '';
        activeStatusDisplay.style.color = recording ? 'red' : 'inherit';
      }
    };
  
    updateButtonStates(false);
  
    // Track focused textarea and associated status element
    document.querySelectorAll('form textarea').forEach(textarea => {
      textarea.addEventListener('focus', () => {
        activeTextarea = textarea;
        const form = activeTextarea.closest('form');
        activeStatusDisplay = form?.querySelector('.recording-status');
      });
    });
  
    // Record button logic
    recordButtons.forEach(button => {
      button.addEventListener('click', async () => {
        if (isRecording) return;
        if (!activeTextarea) {
          alert(gettext('Please click inside a text field before recording.'));
          return;
        }
  
        isRecording = true;
        updateButtonStates(true);
  
        try {
          mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  
          //const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' :
          //                 MediaRecorder.isTypeSupported('audio/ogg') ? 'audio/ogg' : null;
  

          const supportedMimeTypes = [
            'audio/mp4',         // Preferred for Safari/iOS (uses AAC codec)
            'audio/webm',        // Good for Chrome/Android/Firefox
            'audio/ogg'          // Fallback
          ];

          let mimeType = null;

          for (const type of supportedMimeTypes) {
              if (MediaRecorder.isTypeSupported(type)) {
                  mimeType = type;
                  break;
              }
          }

          if (!mimeType) {
            alert(gettext('Your browser does not support audio recording.'));
            throw new Error('Unsupported MIME type for MediaRecorder.');
          }
  
          mediaRecorder = new MediaRecorder(mediaStream, { mimeType: mimeType });
          audioChunks = [];
  
          mediaRecorder.ondataavailable = e => {
            if (e.data.size > 0) audioChunks.push(e.data);
          };
  
          mediaRecorder.onstop = async () => {
            isRecording = false;
            updateButtonStates(false);
  
            if (activeStatusDisplay) {
              activeStatusDisplay.textContent = gettext('Processing transcription...');
              activeStatusDisplay.style.color = 'blue';
            }
  
            if (mediaStream) {
              mediaStream.getTracks().forEach(track => track.stop());
              mediaStream = null;
            }
  
            
            // 1. Create the original Blob using the browser's reported MIME type
            let blob = new Blob(audioChunks, { type: mimeType });
            
            if (blob.type.startsWith('video/')) {
                blob = new Blob(audioChunks, { type: 'audio/mp4' });
            }

            const finalMimeType = blob.type;

            const formData = new FormData();

            formData.append('audio', blob, `recording.${finalMimeType.split('/')[1]}`);
            
            //const blob = new Blob(audioChunks, { type: mimeType });

            //// SAFARI PWA FIX
            //let finalMimeType = mimeType;

            //if (finalMimeType.startsWith('video/') && finalMimeType.includes('mp4')) {
            //    finalMimeType = 'audio/mp4';
            //}


            //const formData = new FormData();

            //// Use the corrected MIME type for the third argument (filename extension)
            //formData.append('audio', blob, `recording.${finalMimeType.split('/')[1]}`);

            //formData.append('audio', blob, `recording.${mimeType.split('/')[1]}`);
  



            const csrftoken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            try {
              const response = await fetch('/transcribe-audio/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken, // Add this header
                    // No need for 'Content-Type' header for FormData, requests handles it
                  },
                body: formData
              });
  
              if (!response.ok) {
                const errorText = await response.text();
                console.error('Error:', errorText);
                alert(gettext('An error occurred: ') + errorText);
                return;
              }
  
              const data = await response.json();
              if (data.transcript && activeTextarea) {
                activeTextarea.value += (activeTextarea.value ? '\n' : '') + data.transcript;

                // Manually trigger input event for auto-resize script
                activeTextarea.dispatchEvent(new Event('input', { bubbles: true }));
              }
            } catch (err) {
              alert(gettext('Transcription failed: ') + err.message);
              console.error('Transcription error:', err);
            } finally {
              if (activeStatusDisplay) activeStatusDisplay.textContent = '';
            }
          };
  
          mediaRecorder.start();
        } catch (err) {
          isRecording = false;
          updateButtonStates(false);
          if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
            mediaStream = null;
          }
          console.error('Recording start error:', err);
          alert(gettext('Could not start recording. Check microphone permissions.'));
        }
      });
    });
  
    // Stop button logic
    stopButtons.forEach(button => {
      button.addEventListener('click', () => {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
          mediaRecorder.stop();
        }
      });
    });
  });
  