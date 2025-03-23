async function uploadCurriculum() {
    const fileInput = document.querySelector('#curriculumForm input[type="file"]');
    const statusDiv = document.getElementById('status');
    
    // Проверка выбранного файла
    if (!fileInput.files[0]) {
        showStatus('Выберите файл для загрузки!', 'danger');
        return;
    }

    // Проверка расширения файла
    const fileName = fileInput.files[0].name.toLowerCase();
    if (!fileName.endsWith('.xlsx')) {
        showStatus('Формат файла не поддерживается. Загрузите .xlsx файл', 'danger');
        return;
    }

    const formData = new FormData(document.getElementById('curriculumForm'));
    formData.append('sheets', 'ПланСвод,План');

    try {
        // Показать статус загрузки
        showStatus('Идёт обработка файла...', 'info');
        
        // Блокировка кнопки
        const submitBtn = document.querySelector('#curriculumForm button');
        submitBtn.disabled = true;

        const response = await fetch('/api/upload-curriculum', {
            method: 'POST',
            body: formData
        });

        // Обработка HTTP-ошибок
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`${response.status}: ${errorText || 'Неизвестная ошибка'}`);
        }

        // Обработка бизнес-логики ошибок
        const result = await response.json();
        if (result.error) {
            throw new Error(result.error);
        }

        // Успешная загрузка
        showStatus(`Загружено ${result.imported} записей`, 'success');
        fileInput.value = ''; // Сброс выбора файла
        
        // Обновление таблицы
        await loadCurriculum();
        
    } catch (error) {
        // Обработка ошибок сети и парсинга
        const errorMessage = error.message.includes('Unexpected token') 
            ? 'Некорректный формат ответа сервера' 
            : error.message;
            
        showStatus(`Ошибка: ${errorMessage}`, 'danger');
    } finally {
        // Разблокировать кнопку
        const submitBtn = document.querySelector('#curriculumForm button');
        if (submitBtn) submitBtn.disabled = false;
    }
}