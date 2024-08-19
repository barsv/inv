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

camera.position.set(0, 0, 50);
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

    // Затухание скорости для плавного остановки
    velocity.multiplyScalar(0.9);
}

// Добавление осей координат
var axesHelper = new THREE.AxesHelper(10);
scene.add(axesHelper);

// Функция для построения графика
function buildChart(data) {
    var closePrices = data.close;
    var volumes = data.vol;

    // Создаем массивы для вершин и индексов
    var vertices = [];
    var indices = [];

    // Добавление точек на график
    for (let i = 0; i < closePrices.length; i++) {
        var x = i;
        var y = 2 * closePrices[i] / 29257.5;
        var z = 2 * volumes[i] / 1007238; // Масштабируем объемы для удобства визуализации

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

    // Построение объемных баров
    for (let i = 0; i < volumes.length; i++) {
        var barGeometry = new THREE.BoxGeometry(0.8, 0.8, volumes[i] / 10000);
        var barMaterial = new THREE.MeshBasicMaterial({ color: 0x0000ff });
        var bar = new THREE.Mesh(barGeometry, barMaterial);
        bar.position.set(i, closePrices[i], volumes[i] / 20000); // Коррекция позиции
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
