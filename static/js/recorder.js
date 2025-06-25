document.addEventListener('DOMContentLoaded', () => {
    const recordButton = document.getElementById('recordButton');
    const processButton = document.getElementById('processButton');
    const status = document.getElementById('status');
    const audioForm = document.getElementById('audio-form');

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Your browser does not support audio recording.');
        return;
    }

    let mediaRecorder;
    let audioChunks = [];

    recordButton.addEventListener('click', async () => {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const audioFile = new File([audioBlob], "recording.wav", { type: 'audio/wav' });
            
            // Use a DataTransfer object to create a FileList
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(audioFile);

            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.name = 'audio_data';
            fileInput.files = dataTransfer.files;

            audioForm.appendChild(fileInput);
            audioForm.submit();
        };

        mediaRecorder.start();
        status.textContent = 'Recording... Press "Stop and Process" to finish.';
        recordButton.style.display = 'none';
        processButton.style.display = 'inline-block';
        audioForm.classList.remove('hidden');
    });

    // We submit the form directly on stop now, so this button is the trigger
    processButton.addEventListener('click', (e) => {
        e.preventDefault(); // Prevent default form submission
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            status.textContent = 'Processing... Please wait.';
            processButton.disabled = true;
            mediaRecorder.stop();
        }
    });
});