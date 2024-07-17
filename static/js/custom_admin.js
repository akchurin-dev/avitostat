document.addEventListener('DOMContentLoaded', function() {
    const button = document.getElementById('custom-button');
    button.addEventListener('click', function() {
        const objectId = button.getAttribute('data-object-id');
        console.log("Instance ID:", objectId);

        fetch(`http://45.12.238.229:8000/messaging/bad_messaging_week_report_individual/${objectId}`, {
            method: 'GET',
        })
        .then(response => response.json())
        .then(data => {
            console.log('Success:', data);
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    });
});
