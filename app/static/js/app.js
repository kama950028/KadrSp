async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const statusDiv = document.getElementById('status');
    
    if (!fileInput.files[0]) {
        showStatus('Выберите файл!', 'danger');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        showStatus('Идет импорт данных...', 'info');
        
        // Отправка файла на сервер
        const response = await fetch('/import/teachers', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Ошибка: ${response.statusText}`);
        }

        showStatus('Импорт завершен, ожидаем данные...', 'info');
        await pollTeachers(); // Проверяем, появились ли данные
    } catch (error) {
        showStatus(`Ошибка: ${error.message}`, 'danger');
    }
}

async function loadTeachers() {
    try {
        const response = await fetch('/api/teachers'); // Предполагается, что есть API для получения данных
        const teachers = await response.json();

        const teachersList = document.getElementById('teachersList');
        teachersList.innerHTML = ''; // Очищаем таблицу перед заполнением

        teachers.forEach(teacher => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${teacher.full_name}</td>
                <td>${teacher.position}</td>
                <td>${teacher.total_experience}</td>
                <td>${teacher.teaching_experience}</td>
                <td>${teacher.professional_experience}</td>
                <td>${teacher.education_level}</td>
                <td>${teacher.academic_degree}</td>
                <td>${teacher.academic_title}</td>
                <td>${teacher.disciplines_raw}</td>
                <td>${teacher.qualifications_raw}</td>
                <td>${teacher.programs_raw}</td>
            `;
            teachersList.appendChild(row);
        });
    } catch (error) {
        console.error('Ошибка загрузки преподавателей:', error);
    }
}

// // Загружаем преподавателей при загрузке страницы
// document.addEventListener('DOMContentLoaded', loadTeachers);

async function pollTeachers(interval = 2000, maxAttempts = 10) {
    let attempts = 0;

    while (attempts < maxAttempts) {
        try {
            const response = await fetch('/api/teachers');
            if (response.ok) {
                const teachers = await response.json();
                if (teachers.length > 0) {
                    teachersData = teachers; // Сохраняем данные
                    teachersData.sort((a, b) => {
                        if (a.full_name < b.full_name) return -1;
                        if (a.full_name > b.full_name) return 1;
                        return 0;
                    });
                    renderTeachersTable(teachersData); // Отображаем таблицу
                    showStatus('Данные успешно загружены!', 'success');
                    return;
                }
            }
        } catch (error) {
            console.error('Ошибка при проверке данных:', error);
        }

        attempts++;
        await new Promise(resolve => setTimeout(resolve, interval)); // Ждем перед следующей попыткой
    }

    showStatus('Не удалось загрузить данные. Попробуйте обновить страницу.', 'danger');
}

let teachersData = []; // Глобальная переменная для хранения данных преподавателей
let isAscending = true; // Флаг для переключения направления сортировки

function sortTeachersByName() {
    // Сортируем массив преподавателей по ФИО
    teachersData.sort((a, b) => {
        if (a.full_name < b.full_name) return isAscending ? -1 : 1;
        if (a.full_name > b.full_name) return isAscending ? 1 : -1;
        return 0;
    });
    
    isAscending = !isAscending; // Переключаем направление сортировки
    renderTeachersTable(teachersData); // Обновляем таблицу
}

function renderTeachersTable(teachers) {
    const tbody = document.getElementById('teachersList');
    tbody.innerHTML = ''; // Очистка таблицы перед добавлением данных
    
    teachers.forEach(teacher => {
        const qualifications = teacher.qualifications.map(q => q.name).join(', ');
        tbody.innerHTML += `
            <tr>
                <td>${teacher.full_name}</td>
                <td>${teacher.position}</td>
                <td>${teacher.education_level}</td>
                <td>${qualifications}</td>
            </tr>
        `;
    });
}

document.addEventListener('DOMContentLoaded', loadTeachers);

function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('status');
    statusDiv.style.display = 'block';
    statusDiv.className = `alert alert-${type}`;
    statusDiv.textContent = message;
    
    if (type !== 'info') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
}

document.addEventListener('DOMContentLoaded', loadTeachers);