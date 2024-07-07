trailing_stop_loss_percent = 0.1 * 0.01

def get_trailing_stop_loss_long_profits(df):
    """
    на каждом баре считаем, что мы делаем открытие по цене open и запускаем реплей пока не сработает скользящий сл.
    после срабатывания сл подсчитываем профит, вычитая цену открытия из цены сл.
    считаем, что на нулевом баре по стоп лоссу закрытия не будет. т.е. не будет такого, что после открытия цена пошла 
    вверх, обновила стоплосс, а потом пошла вниз и пробила его. на практике такое конечно возможно, но будем считать, 
    что анализ стоплосса не будет производиться на том баре, где было открытие.
    выбираю такую логику, т.к. не хочу, чтобы происходили срабатывания сл там, где их не было. 
    например, если цена была в боковике с минимальной волатильностью, а 
    потом появилась большая свеча вверх, то если обновить на этой свече сл и сразу сравнить с лоу на этой же свече, то
    получится закрытие по сл, которого на самом деле не было.
    теперь рассмотрим симметричную ситуацию, когда после боковика появилась огромная свеча вниз. мы не будем сравнивать
    лоу с сл и не сделаем закрытие, которое должно было быть. однако, на следующей свече возможны два кейса:
    1) цена продолжила падать. поэтому закрытие таки состоится, причем засчитается оно по сл предыдущей свечи, т.е.
    размер профита получится такой же как если бы считали срабатывание сл на предыдущей свече.
    2) цена внезапно пойдет вверх. т.е. сначала она жахнула вниз, а потом сразу вернулась назад. причем случилось это
    на свече, где было открытие позиции. т.е. такая сильная неудача. в этом случае с текущим алгоритмом мы пропустим 
    срабатывание такого сл, когда на самом деле было закрытие, но оно не засчиталось. однако, если открытие было на 
    каких-то предыдущих свечах, а не на этой редкой неудачной свече, то все посчитается верно. сл сработает, т.к. цена
    сл будет рассчитана на предыдущем баре, а на текущем с сильным движением вниз пройзойдет сравнение старого сл
    с новым лоу и засчитается закрытие.
    я предполагаю, что такие ситуации, когда случилось открытие, пробив сл вниз и возврат цены настолько редкими, что
    ими можно пренебречь. т.к. чтобы полностью правильно определять закрытие по сл, то надо смотреть в 
    тиковые данные. это усложнит код и я ожидаю, что не значительно улучшит результат. особенно при правильно выбранном 
    размере сл.
    """
    opens = df['open'].to_numpy()
    highs = df['high'].to_numpy()
    lows = df['low'].to_numpy()

    n = len(opens)
    profits = []
    stop_loss_prices = []
    maximums = []
    """ # idea: 
    # x0 - start of the trade. 
    # x1 - end of the trade.
    # начинаем идти по х. продвигаем пока не конец данных.
    # от текущего хая межу х0 и х1 считаем стоплосс. макс хай сохраняем.
    # если лоу ниже сл, останавливаемся. 
    # все, то до макс хай закрывается на текущем x1. т.е. нет смысла там повторять рассчет с начала, можно сразу сказать
    # размер профита.
    # все, что между макс хай и х1 закроется на х1 или позже. (на х1 может закрыться если размер сл на баре следующем за
    # макс хай сл окажется выше лоу на х1). т.е. нет смысла проводить эксперимент между макс хай и х1, можно начинать с 
    """
    x0 = 0
    x1 = 0
    while x1 < n:
        """ # starting from the current position look forward for trailing stop loss closing.
            # assume that current position will not get closed on the current bar. it's not always true but ... lets assume 
            # because if we close a position on the same bar where we opened the position then sl is wrong. also if we
            # de-facto close the position on the same bar where we opened it and we don't count it here as closed then lets 
            # think what can happen next. the bar has to be huge to be bigger than SL. after such a big move from the high 
            # to the SL price it seems unlikely that the price will just revert and will result in a profitable trade. most 
            # likely if we by algorithm mistake didn't close the position then it will be closed on the next bar and the 
            # result still will be the same.
            # collect intermediate results
        """
        print(x0)
        max_high_x = x0
        max_high = highs[max_high_x]
        sl_size = max_high * trailing_stop_loss_percent
        sl_price = max_high - sl_size
        local_maximums = [max_high]
        local_stop_loss_prices = [sl_price]
        if x1 == x0:
            x1 += 1
        # is_sl = False
        while x1 < n and lows[x1] > sl_price:
            # # if price went lower than current stop loss then assume that the position was closed at the stop loss price.
            # if is_sl:
            #     """ # dump results.
            #     # all openings between the current opening x0 and the max_high_x will be closed on the same stop loss position.
            #     """
            #     while x0 <= max_high_x:
            #         profits.append(sl_price - opens[x0])
            #         x0 += 1
            # even if is_sl we update max_high and sl_price for the current x1 bar and move to the next x1.
            # if there is a new max_high then save it, it's position and recalculate trailing stop loss.
            if max_high < highs[x1]:
                max_high_x = x1
                max_high = highs[max_high_x]
                sl_size = max_high * trailing_stop_loss_percent
                sl_price = max_high - sl_size
            local_stop_loss_prices.append(sl_price)
            local_maximums.append(max_high)
            x1 += 1
        if x1 == n:
            break
        x = x0
        while x <= max_high_x:
            profits.append(sl_price - opens[x])
            stop_loss_prices.append(local_stop_loss_prices[x - x0])
            maximums.append(local_maximums[x - x0])
            x += 1
        x0 = max_high_x + 1
    while x0 < n:
        profits.append(None)
        stop_loss_prices.append(None)
        maximums.append(None)
        x0 += 1
    return (profits, stop_loss_prices, maximums)


# (profits, stop_loss_prices, maximums) = get_trailing_stop_loss_long_profits(df)
# data['profit'] = profits
# data['stop_loss_price'] = stop_loss_prices
# data['maximum'] = maximums
# print(len(data))
# print(len(profits))
# print(len(stop_loss_prices))
# print(len(maximums))