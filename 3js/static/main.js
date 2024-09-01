import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

var canvasContainer = document.getElementById('canvas-container');
var scene = new THREE.Scene();
var camera = new THREE.PerspectiveCamera(75, canvasContainer.clientWidth / canvasContainer.clientHeight, 0.1, 1000);

var renderer = new THREE.WebGLRenderer();
renderer.setSize(canvasContainer.clientWidth, canvasContainer.clientHeight);
canvasContainer.appendChild(renderer.domElement);

// Управление камерой
var controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; // Для плавного движения
controls.dampingFactor = 0.05;

camera.position.set(0, 0, 5);
controls.target.set(0, 0, 0); // Устанавливаем начальную точку вращения
controls.update();

// Обработчики для передвижения камеры
var moveForward = false;
var moveBackward = false;
var moveLeft = false;
var moveRight = false;

var velocity = new THREE.Vector3();
var direction = new THREE.Vector3();

var onKeyDown = function (event) {
    switch (event.code) {
        case 'ArrowUp':
        case 'KeyW':
            moveForward = true;
            break;

        case 'ArrowLeft':
        case 'KeyA':
            moveLeft = true;
            break;

        case 'ArrowDown':
        case 'KeyS':
            moveBackward = true;
            break;

        case 'ArrowRight':
        case 'KeyD':
            moveRight = true;
            break;
    }
};

var onKeyUp = function (event) {
    switch (event.code) {
        case 'ArrowUp':
        case 'KeyW':
            moveForward = false;
            break;

        case 'ArrowLeft':
        case 'KeyA':
            moveLeft = false;
            break;

        case 'ArrowDown':
        case 'KeyS':
            moveBackward = false;
            break;

        case 'ArrowRight':
        case 'KeyD':
            moveRight = false;
            break;
    }
};

document.addEventListener('keydown', onKeyDown);
document.addEventListener('keyup', onKeyUp);

function updateMovement() {
    direction.set(0, 0, 0);

    if (moveForward) direction.z += 1;
    if (moveBackward) direction.z -= 1;
    if (moveLeft) direction.x -= 1;
    if (moveRight) direction.x += 1;

    direction.normalize();

    // Перевод направления из системы координат камеры в мировую систему координат
    if (moveForward || moveBackward || moveLeft || moveRight) {
        velocity.addScaledVector(camera.getWorldDirection(new THREE.Vector3()), direction.z * 0.1);
        velocity.addScaledVector(camera.getWorldDirection(new THREE.Vector3()).cross(camera.up), direction.x * 0.1);
    }

    // Обновляем положение камеры и цель для OrbitControls
    controls.object.position.add(velocity);
    controls.target.add(velocity);

    // Обновляем положение куба на точке вращения камеры
    cube.position.copy(controls.target);

    // Затухание скорости для плавного остановки
    velocity.multiplyScalar(0.9);
}

// Добавление осей координат
var axesHelper = new THREE.AxesHelper(10);
scene.add(axesHelper);

// Добавление куба из ребер в точке вращения камеры
var cubeGeometry = new THREE.BoxGeometry(2, 2, 2);
var edges = new THREE.EdgesGeometry(cubeGeometry); // Создаем геометрию ребер
var lineMaterial = new THREE.LineBasicMaterial({ color: 0x00ff00 }); // Материал для линий
var cube = new THREE.LineSegments(edges, lineMaterial); // Создаем линию на основе ребер
scene.add(cube);

function findMinMax(arr) {
    // Инициализация переменных для хранения минимального и максимального значений
    let min = Infinity;
    let max = -Infinity;

    // Проход по массиву для нахождения минимального и максимального значений
    for (let i = 0; i < arr.length; i++) {
        if (arr[i] < min) {
            min = arr[i];
        }
        if (arr[i] > max) {
            max = arr[i];
        }
    }

    // Возвращаем объект с минимальным и максимальным значениями
    return { min, max };
}

const ySize = 10;
// Функция для построения графика
function buildChart(data) {
    var closePrices = data.close;
    var volumes = data.vol;
    var { min: closeMin, max: closeMax } = findMinMax(closePrices);
    var { min: volumeMin, max: volumeMax } = findMinMax(volumes);
    var closeDelta = closeMax - closeMin;
    var volumeDelta = volumeMax - volumeMin;

    // Создаем массивы для вершин и индексов
    var vertices = [];
    var indices = [];

    // Добавление точек на график
    for (let i = 0; i < closePrices.length; i++) {
        var x = ySize * (closePrices[i] - closePrices[0]) / closeDelta;
        // var y = (volumes[i] - volumes[0]) / volumeDelta; // Масштабируем объемы для удобства визуализации
        var y = 0; // Масштабируем объемы для удобства визуализации
        var z = i * 0.01;

        vertices.push(x, y, z);

        // Линия по цене
        if (i > 0) {
            indices.push(i - 1, i);
        }
    }

    // Создание BufferGeometry для линий
    var geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setIndex(indices);

    var lineMaterial = new THREE.LineBasicMaterial({ color: 0x00ff00 });
    var line = new THREE.LineSegments(geometry, lineMaterial);
    scene.add(line);

    // построение объемных баров
    for (let i = 0; i < volumes.length; i++) {
        var bargeometry = new THREE.BoxGeometry(0.02, (volumes[i] - volumes[0]) / volumeDelta, 0.02);
        var color = i > 0 && closePrices[i] > closePrices[i - 1] ? 0x00ff00 : 0xff0000;
        var barmaterial = new THREE.MeshBasicMaterial({ color });
        var bar = new THREE.Mesh(bargeometry, barmaterial);
        bar.position.set(
            ySize * (closePrices[i] - closePrices[0]) / closeDelta,
            (volumes[i] - volumes[0]) / volumeDelta / 2,
            i * 0.01
        ); // коррекция позиции
        scene.add(bar);
    }
}

var animate = function () {
    requestAnimationFrame(animate);
    updateMovement(); // Обновление передвижения
    controls.update();
    renderer.render(scene, camera);
};

animate();

// Получение данных и построение графика
fetch('/ohlc-data')
    .then(response => response.json())
    .then(data => {
        console.log(data);
        buildChart(data);
    })
    .catch(error => console.error('Error fetching OHLC data:', error));
