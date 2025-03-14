в этом проекте мы работаем над идеей использования фазового пространства для создания торгового робота.

работа началась в простом чате, но тот чат стал слишком длинным. из-за размера начал тормозить веб интерфейс. и еще у меня есть подозрение, что начал теряться контекст. поэтому я перенес работу в этот проект.

Ниже я собрал основное, что мы успели обсудить и сделать за всё время обсуждений — от первых идей до текущего состояния. Надеюсь, это поможет создать контекст для будущих чатов.

1. Отправная точка: MACD, индикаторы, фракталы, хаос
Начало: разговор шёл о том, что при простом использовании MACD/скользящих средних/такенсовых вложений получается «фигня» (фазовый портрет получается плоским и вытянутым, требуется дополнительная обработка/перемасштабирование). Хотелось понять, почему так и есть ли научные статьи про MACD, случайное блуждание, теорию хаоса, фракталы и т. д.
Обсудили методы нелинейной динамики, странные аттракторы, попытки их применять к финансам.
Вывод: классические методы (MACD, RSI) часто дают результат только при определённых рыночных режимах, а хаотические подходы (странные аттракторы, ляпуновские показатели) не всегда дают практический результат в реальных (шумных) данных.
2. Идея фазового портрета
Сначала мы пробовали строить фазовый портрет, просто беря цены с задержками Такенса. Результат оказался почти линейной диагональю.
Затем перешли к тому, чтобы брать разность сглаженных цен (SMA, EMA или Savitzky-Golay) и её производную, чтобы убрать тренд и получить более «колебательную» структуру.
Пробовали разные варианты сглаживания (Savitzky-Golay, разная длина окна). Это дало чуть более внятные эллипсы, но всё ещё шумно.
3. Разность сглаженных средних, производная и вторая производная
Поняли, что одной производной бывает мало (траектории пересекаются).
Решили добавить вторую производную → перешли к идее 3D-фазового пространства.
4. Построение кэша переходов в фазовом пространстве
Сделали функцию, которая:

Делит фазовое пространство на сетку.
Для каждой точки t запоминает, куда она попала через τ шагов.
Получается кэш переходов.
Первый вариант (2D): (x,y)=(разность,первая производная).
Второй вариант (3D): (x,y,z), но фактически при обратном преобразовании в цену используем только x.

5. Визуализация прогноза на графике цены
Идея:

Берём текущую точку t → смотрим её клетку в фазовом пространстве.
Из кэша берём все будущие клетки, куда можно прийти через τ шагов.
Переводим клетку обратно в «разность цены», перемножаем на скользящую среднюю и прибавляем текущую цену → получаем будущую цену.
Рисуем scatter plot на графике цены, раскрашиваем по частоте перехода (или вероятности).
Результат:

Множество точек (вертикальные облака) на τ шагов вперёд.
Цвет (красный/синий) показывает, где переходов больше.
6. Технические детали, которые меняли и улучшали
Сглаживание: Savitzky-Golay с разными параметрами.
Кэш: сначала сохраняли полный cell_future, потом — только x-компоненту (уменьшает накладку точек и экономит память).
Сетка: меняли размеры (500x500, 1000x1000, 3D-сетка и т. д.).
Цветовые карты: сначала coolwarm, потом решили попробовать однотонный градиент или cividis.
train/test: разделяли данные, чтобы строить кэш на train, а прогноз на test.
num_points: ограничение количества точек на графике, чтобы не перегружать визуализацию.
Обратное преобразование: future_price=ΔP×smoothed_long[t]+current_price. Это очень грубо и может давать смещение.
7. Возникшие проблемы и вопросы
Не всё покрывается прогнозом: даже если кэш строим на всех данных, бывают участки, где реальная цена остаётся без точек прогноза.
Если увелчивать размерность ФП, то траектории быстро становятся разреженными, т.е. не хватает данных для статистически обоснованного прогноза.
SINDy, нейронные сети: обсуждали, что можно применить, но пока не делали.
8. Отложенные/не реализованные идеи
Автоматический подбор окон сглаживания (например, с помощью ляпуновских показателей, взаимной информации и т. д.).
Суммирование нескольких фазовых портретов (30-60, 60-120, 120-240) для уточнения прогноза. Пока делали только по одному ФП.
Кластеризация (K-Means/DBSCAN) в фазовом пространстве, чтобы улучшить предсказание.
SINDy (Sparse Identification of Nonlinear Dynamics) или другие методы для вывода уравнений.
Учёт изменения smoothed_long (чтобы не считать его постоянным за τ баров).
Итог
У нас получился прототип метода, который:

Реконструирует фазовое пространство по разности сглаженных средних и её производным.
Сохраняет исторические переходы τ шагов вперёд.
Рисует на ценовом графике «облако» возможных будущих цен.
Это даёт интуитивную картину: показывает масштаб разброса прогноза и цветом показыват размазанность (наличие пиков вероятности). 

Дальше можно улучшать этот подход или попробовать другие методы (кластеризация, нейросети, SINDy, логарифмирование, нормализация), но это уже отдельные ветки исследования.


в этом проекте мне важно самому держать код в моей голове. поэтому прошу тебя (если я явно не прошу обратное) предлагать правки не методом переписывания всего кода, а говорить в каком месте, что поменять. чтобы я сам вносил правки и запоминал их.

моя цель в совместной работе с тобой не в том, чтобы ты делал за меня работу, а в том, чтобы обсуждать идеи, т.к. пока мне больше не с кем кроме тебя их обсуждать. ну и твою помощь с python конечно сложно переоценить.

еще прошу тебя говорить свои идеи и предложения, если они у тебя появляются по ходу обсуждения. даже если они выглядят как офф топик. я не обязательно все такие идеи буду пробовать, но буду обдумывать. это очень помогает находить новые направления для исследований.
