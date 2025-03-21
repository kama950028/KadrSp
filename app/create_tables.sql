-- Создание таблицы преподавателей
CREATE TABLE teachers (
    teacher_id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL UNIQUE,
    position VARCHAR(100) NOT NULL,
    education_level VARCHAR(100) NOT NULL,
    qualification VARCHAR(100),
    base_education_specialty VARCHAR(255),
    scientific_education_specialty VARCHAR(255),
    academic_degree VARCHAR(100),
    academic_title VARCHAR(100),
    total_experience INTEGER,
    teaching_experience INTEGER,
    professional_experience INTEGER
);

COMMENT ON TABLE teachers IS 'Основная информация о преподавателях';
COMMENT ON COLUMN teachers.full_name IS 'ФИО преподавателя (уникальное)';

-- Создание таблицы повышения квалификации
CREATE TABLE qualifications (
    qualification_id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    course_name VARCHAR(255) NOT NULL,
    year INTEGER NOT NULL
);

COMMENT ON TABLE qualifications IS 'Курсы повышения квалификации преподавателей';

-- Создание таблицы профессиональной переподготовки
CREATE TABLE retrainings (
    retraining_id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    program_name VARCHAR(255) NOT NULL,
    year INTEGER NOT NULL
);

COMMENT ON TABLE retrainings IS 'Программы профессиональной переподготовки';

-- Создание таблицы образовательных программ
CREATE TABLE education_programs (
    program_id SERIAL PRIMARY KEY,
    program_name VARCHAR(255) NOT NULL UNIQUE
);

COMMENT ON TABLE education_programs IS 'Образовательные программы вуза';

-- Создание таблицы связи преподавателей и программ (многие-ко-многим)
CREATE TABLE teacher_programs (
    teacher_id INTEGER NOT NULL REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    program_id INTEGER NOT NULL REFERENCES education_programs(program_id) ON DELETE CASCADE,
    PRIMARY KEY (teacher_id, program_id)
);

COMMENT ON TABLE teacher_programs IS 'Связь преподавателей с образовательными программами';

-- Создание таблицы преподаваемых дисциплин
CREATE TABLE taught_disciplines (
    discipline_id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    discipline_name VARCHAR(255) NOT NULL
);

COMMENT ON TABLE taught_disciplines IS 'Дисциплины, которые ведут преподаватели';

-- Создание индексов
CREATE INDEX idx_teachers_full_name ON teachers (full_name);
CREATE INDEX idx_qualifications_teacher ON qualifications (teacher_id);
CREATE INDEX idx_retrainings_teacher ON retrainings (teacher_id);