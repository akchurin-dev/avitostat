document.addEventListener('DOMContentLoaded', function () {
    const inlineRows = document.querySelectorAll('.inline-related');

    inlineRows.forEach(row => {
        const integrationField = row.querySelector('[name$="integration_id"]');
        if (integrationField) {
            const input = document.createElement('input');
            input.type = 'text';
            input.placeholder = 'Введите ID интеграции';
            input.style.marginRight = '10px';

            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = 'Подключить';
            button.classList.add('button');
            button.style.marginTop = '10px';

            integrationField.parentElement.appendChild(input);
            integrationField.parentElement.appendChild(button);

            button.addEventListener('click', () => {
                const clientId = input.value.trim();
                if (clientId) {
                    try {
                        const requestData = {
                            client_id: clientId,
                            state: 123 // или любое другое необходимое состояние
                        };

                        fetch('/amocrm_oauth', {
                            method: 'POST', // или 'GET', если ваш эндпоинт работает через GET
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify(requestData)
                        })
                        .then(response => {
                            if (!response.ok) {
                                throw new Error(`Ошибка сервера: ${response.status}`);
                            }
                            return response.json();
                        })
                        .then(data => {
                            console.log('Успех:', data);
                            alert('Интеграция выполнена успешно!');
                        })
                        .catch(error => {
                            console.error('Ошибка:', error);
                            alert('Произошла ошибка при интеграции.');
                        });
                    } catch (error) {
                        console.error('Ошибка обработки:', error);
                        alert('Произошла ошибка при выполнении операции.');
                    }
                } else {
                    alert('Пожалуйста, введите ID интеграции.');
                }
            });
        }
    });
});

// Функция для получения CSRF-токена (если используется Django)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
