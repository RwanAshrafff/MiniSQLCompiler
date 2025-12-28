CREATE TABLE students (
    id INT,
    name TEXT,
    gpa FLOAT
);
CREATE TABLE students (
    id INT,
    name TEXT,
    gpa FLOAT
);

insert into students vALUES ('go', 'Rwan', 2);
INSERT INTO students VALUES (1, 'Samer', 3);
INSERt INTO students VALUES (1, 'Zaynab', 3.5);
INSERT INTO students VALUES (1, 'Abduallah', 3.9);
SELECT name, gpa FROM students WHERE gpa > 3.5;
SELECT * FROM students WHERE name < 50;