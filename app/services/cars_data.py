import aiohttp
import re
from typing import List, Tuple, Optional
from rapidfuzz import fuzz, process
from functools import lru_cache
import asyncio

POPULAR_BRANDS = [
    'Toyota', 'Honda', 'Nissan', 'Mazda', 'Subaru', 'Mitsubishi', 'Lexus', 'Infiniti', 'Suzuki', 'Daihatsu',
    'BMW', 'Audi', 'Mercedes-Benz', 'Volkswagen', 'Opel', 'Porsche', 'Smart', 'Mini', 'Maybach', 'MAN',
    'Ford', 'Chevrolet', 'Jeep', 'Tesla', 'Cadillac', 'Buick', 'GMC', 'Lincoln', 'Chrysler', 'Dodge', 'Ram',
    'Hyundai', 'Kia', 'Genesis', 'SsangYong', 'Daewoo',
    'Renault', 'Peugeot', 'Citroen', 'Dacia', 'Alpine',
    'Skoda',
    'Fiat', 'Alfa Romeo', 'Lancia', 'Ferrari', 'Lamborghini', 'Maserati',
    'Volvo',
    'Seat', 'Cupra',
    'Land Rover', 'Jaguar', 'Rolls-Royce', 'Bentley', 'Aston Martin', 'Lotus', 'McLaren',
    'Lada', 'ВАЗ', 'Лада', 'ГАЗ', 'УАЗ', 'ЗАЗ', 'ТагАЗ', 'Москвич', 'Moskvich',
    'Haval', 'Geely', 'Chery', 'BYD', 'Changan', 'Great Wall', 'FAW', 'Dongfeng', 'Brilliance', 'JAC', 'Lifan', 'Zotye',
    'GAC', 'Exeed', 'Jaecoo', 'Omoda', 'Jetour', 'Zeekr', 'Nio', 'Xpeng', 'Li Auto', 'AITO', 'Seres', 'Hongqi',
    'Voyah', 'Lynk & Co', 'Wey', 'ORA', 'Kaiyi', 'Foton', 'Haima', 'Yema', 'Landwind', 'Soueast', 'Baojun', 'Roewe',
    'Maxus', 'Wuling', 'MG', 'Leapmotor', 'Aiways', 'Geometry', 'Skywell', 'Arcfox', 'Cowin', 'Foday', 'Jonway',
    'Isuzu', 'Scania', 'Iveco', 'Kenworth', 'Peterbilt', 'Mack', 'Freightliner', 'Western Star',
    'Tata', 'Mahindra', 'Maruti Suzuki', 'Hindustan', 'Premier', 'Force', 'Bajaj',
    'Proton', 'Perodua', 'VinFast', 'Moskvich', 'ГАЗель', 'Соболь', 'Валдай', 'Foton', 'JMC', 'DFSK', 'Dayun', 'ZX Auto',
]

RUSSIAN_NAMES = {
    'TOYOTA': 'Тойота', 'HONDA': 'Хонда', 'BMW': 'БМВ', 'AUDI': 'Ауди',
    'MERCEDES-BENZ': 'Мерседес-Бенц', 'MERCEDES': 'Мерседес', 'FORD': 'Форд',
    'NISSAN': 'Ниссан', 'HYUNDAI': 'Хендай', 'KIA': 'Киа', 'VOLKSWAGEN': 'Фольксваген',
    'MAZDA': 'Мазда', 'LEXUS': 'Лексус', 'SUBARU': 'Субару', 'JEEP': 'Джип',
    'VOLVO': 'Вольво', 'PORSCHE': 'Порше', 'MITSUBISHI': 'Митсубиси',
    'PEUGEOT': 'Пежо', 'RENAULT': 'Рено', 'CITROEN': 'Ситроен', 'FIAT': 'Фиат',
    'SKODA': 'Шкода', 'SEAT': 'Сеат', 'OPEL': 'Опель', 'SUZUKI': 'Сузуки',
    'DACIA': 'Дачия', 'LADA': 'Лада', 'VAZ': 'ВАЗ', 'GAZ': 'ГАЗ', 'UAZ': 'УАЗ',
    'HAVAL': 'Хавейл', 'GEELY': 'Джили', 'CHERY': 'Чери', 'BYD': 'БиВиДи',
    'CHANGAN': 'Чанган', 'GREAT WALL': 'Грейт Волл', 'FAW': 'ФАВ',
    'DONGFENG': 'Донгфенг', 'BRILLIANCE': 'Бриллианс', 'JAC': 'ЖАК',
    'LIFAN': 'Лифан', 'ZOTYE': 'Зотие', 'GAC': 'ГАК', 'EXEED': 'Эксид',
    'JAECOO': 'Жако', 'OMODA': 'Омода', 'JETOUR': 'Джетур', 'ZEEKR': 'Зикр',
    'NIO': 'Нио', 'XPENG': 'Кспенг', 'LI AUTO': 'Ли Ауто', 'AITO': 'Айто',
    'SERES': 'Серес', 'HONGQI': 'Хонгки', 'VOYAH': 'Воя', 'LYNK & CO': 'Линк энд Ко',
    'WEY': 'Вей', 'ORA': 'Ора', 'KAIYI': 'Кайи',
    'HAIMA': 'Хайма', 'YEMA': 'Йема', 'LANDWIND': 'Лэндвинд', 'SOUEAST': 'Соуист',
    'BAOJUN': 'Баоджун', 'ROEWE': 'Роув', 'MAXUS': 'Максус', 'WULING': 'Вулинг',
    'MG': 'МГ', 'LEAPMOTOR': 'Липмото', 'AIWAYS': 'Айвейс',
    'TESLA': 'Тесла', 'CHEVROLET': 'Шевроле', 'CADILLAC': 'Кадиллак',
    'BUICK': 'Бьюик', 'GMC': 'ДжиЭмСи', 'LINCOLN': 'Линкольн',
    'CHRYSLER': 'Крайслер', 'DODGE': 'Додж', 'RAM': 'Рам',
    'ALFA ROMEO': 'Альфа Ромео', 'LANCIA': 'Ланча', 'FERRARI': 'Феррари',
    'LAMBORGHINI': 'Ламборгини', 'MASERATI': 'Мазерати',
    'ROLLS-ROYCE': 'Роллс-Ройс', 'BENTLEY': 'Бентли', 'ASTON MARTIN': 'Астон Мартин',
    'LOTUS': 'Лотус', 'MCLAREN': 'Макларен',
    'ISUZU': 'Исузу', 'SCANIA': 'Скания', 'IVECO': 'Ивеко',
    'TATA': 'Тата', 'MAHINDRA': 'Махиндра', 'MOSKVICH': 'Москвич', 'GAZEL': 'Газель',
    'SOBOL': 'Соболь', 'VALDAY': 'Валдай','FOTON': 'Фотон', 'JMC': 'ДжиЭмСи',
    'DFSK': 'ДиЭфЭсКей', 'DAYUN': 'Даюн', 'ZX AUTO': 'ЗетИкс Авто',
}

RUSSIAN_MODELS = {
    'OCTAVIA': 'Октавия', 'FABIA': 'Фабия', 'SUPERB': 'Суперб', 'RAPID': 'Рапид',
    'KODIAQ': 'Кодиак', 'KAROQ': 'Карок', 'SCALA': 'Скала', 'KAMIQ': 'Камик',
    'ENYAQ': 'Эниак', 'KUSHAQ': 'Кушак', 'SLAVIA': 'Славия',
    'GRANTA': 'Гранта', 'VESTA': 'Веста', 'XRAY': 'Иксрей', 'LARGUS': 'Ларгус',
    'NIVA': 'Нива', '4X4': '4х4', 'PRIORA': 'Приора', 'KALINA': 'Калина',
    'SAMARA': 'Самара', 'OKA': 'Ока', 'MOSKVICH 3': 'Москвич 3', 'MOSKVICH 6': 'Москвич 6',
    'A3': 'А3', 'A4': 'А4', 'A6': 'А6', 'A8': 'А8', 'Q3': 'Кью 3', 'Q5': 'Кью 5', 'Q7': 'Кью 7', 'Q8': 'Кью 8',
    'ETRON': 'Е-трон', 'RS6': 'РС6', 'RS7': 'РС7', 'TT': 'ТТ', 'R8': 'Р8',
    '3 SERIES': '3 Серии', '5 SERIES': '5 Серии', '7 SERIES': '7 Серии',
    'X1': 'Икс 1', 'X3': 'Икс 3', 'X5': 'Икс 5', 'X7': 'Икс 7', 'X6': 'Икс 6',
    'M3': 'М3', 'M5': 'М5', 'M8': 'М8', 'i3': 'ай3', 'i4': 'ай4', 'i7': 'ай7', 'iX': 'айИкс',
    'CAMRY': 'Камри', 'COROLLA': 'Королла', 'RAV4': 'РАВ4', 'HIGHLANDER': 'Хайлендер',
    'LAND CRUISER': 'Ленд Крузер', 'PRADO': 'Прадо', 'HILUX': 'Хайлюкс', 'AVALON': 'Авалон',
    'PRIUS': 'Приус', 'C-HR': 'С-ХР', 'YARIS': 'Ярис', 'GR YARIS': 'ДжиАр Ярис',
    'SUPRA': 'Супра', '86': '86', 'GR86': 'ДжиАр86',
    'GOLF': 'Гольф', 'PASSAT': 'Пассат', 'TIGUAN': 'Тигуан', 'POLO': 'Поло',
    'JETTA': 'Джетта', 'TOUAREG': 'Туарег', 'ARTEON': 'Артеон', 'ID.3': 'АйДи 3',
    'ID.4': 'АйДи 4', 'ID.6': 'АйДи 6', 'ID.7': 'АйДи 7', 'TUAREG': 'Туарег',
    'QASHQAI': 'Кашкай', 'X-TRAIL': 'Икс-Трейл', 'JUKE': 'Джук', 'PATROL': 'Патруль',
    'TERRANO': 'Террано', 'ALMERA': 'Альмера', 'MURANO': 'Мурано', 'GT-R': 'ДжиТи-Р',
    'Z': 'З', 'SKYLINE': 'Скайлайн', 'LEAF': 'Лиф',
    'SOLARIS': 'Солярис', 'ELANTRA': 'Элантра', 'TUCSON': 'Тусон', 'SANTA FE': 'Санта Фе',
    'CRETA': 'Крета', 'ACCENT': 'Акцент', 'SONATA': 'Соната', 'IONIQ': 'Айоник',
    'KONA': 'Коная', 'PALISADE': 'Палисад', 'STARIA': 'Стария',
    'RIO': 'Рио', 'CERATO': 'Церато', 'SPORTAGE': 'Спортейдж', 'SORENTO': 'Соренто',
    'OPTIMA': 'Оптима', 'STINGER': 'Стингер', 'SELTOS': 'Селтос', 'EV6': 'ИВи 6',
    'CARNIVAL': 'Карнивал', 'NIRO': 'Ниро', 'SOUL': 'Соул',
    'FOCUS': 'Фокус', 'FIESTA': 'Фиеста', 'MONDEO': 'Мондео', 'KUGA': 'Куга',
    'EXPLORER': 'Эксплорер', 'MUSTANG': 'Мустанг', 'F-150': 'Ф-150', 'RANGER': 'Рейнджер',
    'BRONCO': 'Бронко', 'MAVERICK': 'Маверик', 'TRANSIT': 'Транзит',
    'LOGAN': 'Логан', 'SANDERO': 'Сандеро', 'DUSTER': 'Дастер', 'KAPTUR': 'Каптур',
    'ARKANA': 'Аркана', 'MEGANE': 'Меган', 'KANGOO': 'Кангу', 'TRAFIC': 'Трафик',
    'MASTER': 'Мастер', 'TWINGO': 'Твинго', 'ZOE': 'Зоу',
    'CRUZE': 'Круз', 'AVEO': 'Авео', 'ORLANDO': 'Орландо', 'TRAILBLAZER': 'Трейлблейзер',
    'TAHOE': 'Тахоэ', 'CAMARO': 'Камаро', 'CORVETTE': 'Корвет', 'MALIBU': 'Малибу',
    'EXPRESS': 'Экспресс', 'SILVERADO': 'Сильверадо', 'SUBURBAN': 'Сабурбан',
    'LANCER': 'Лансер', 'OUTLANDER': 'Аутлендер', 'PAJERO': 'Паджеро', 'ASX': 'АСХ',
    'ECLIPSE': 'Эклипс', 'MIRAGE': 'Мираже', 'DELICA': 'Делика',
    '208': '208', '308': '308', '3008': '3008', '5008': '5008', 'PARTNER': 'Партнер',
    'EXPERT': 'Эксперт', 'TRAVELLER': 'Тревеллер', 'BOXER': 'Боксер',
    'C4': 'С4', 'C5': 'С5', 'BERLINGO': 'Берлинго', 'C3': 'С3', 'DS3': 'ДС3',
    'DS4': 'ДС4', 'DS7': 'ДС7', 'JUMPER': 'Джампер',
    'DOBLO': 'Добло', 'DUCATO': 'Дукато', 'PANDA': 'Панда', '500': '500',
    'TIPO': 'Типо', 'FIORINO': 'Фиорино', 'FULLBACK': 'Фулбэк',
    'LEON': 'Леон', 'IBIZA': 'Ибица', 'ATECA': 'Атека', 'ARONA': 'Арона',
    'TARRACO': 'Таррако', 'CUPRAC': 'Купрак',
    'XC60': 'ИКССи 60', 'XC90': 'ИКССи 90', 'S60': 'Эс 60', 'S90': 'Эс 90',
    'V90': 'Ви 90', 'V60': 'Ви 60', 'XC40': 'ИКССи 40',
    'GRAND CHEROKEE': 'Гранд Чероки', 'CHEROKEE': 'Чероки', 'RENEGADE': 'Ренегейд',
    'COMPASS': 'Компас', 'WRANGLER': 'Рэнглер', 'GLADIATOR': 'Гладиатор',
    'RANGE ROVER': 'Рейндж Ровер', 'DISCOVERY': 'Дискавери', 'DEFENDER': 'Дефендер',
    'EVOQUE': 'Эвок', 'VELAR': 'Велар', 'SPORT': 'Спорт',
    'F-PACE': 'Эф-Пейс', 'XE': 'ИКСи', 'XF': 'ИКСи Эф', 'XJ': 'ИКСи Джей',
    'CAYENNE': 'Кайен', 'MACAN': 'Макан', 'PANAMERA': 'Панамера',
    '911': '911', 'TAYCAN': 'Тайкан', 'BOXSTER': 'Бокстер', 'CAYMAN': 'Кайман',
    'MODEL 3': 'Модель 3', 'MODEL Y': 'Модель Y', 'MODEL S': 'Модель S', 'MODEL X': 'Модель X',
    'CYBERTRUCK': 'Кибертрак', 'ROADSTER': 'Роудстер',
    'COOPER': 'Купер', 'COUNTRYMAN': 'Кантримен', 'CLUBMAN': 'Клабмен',
    'FORTWO': 'Фортво', 'FORFOUR': 'Форфоур',
    'REXTON': 'Рекстон', 'ACTYON': 'Актьон', 'KYRON': 'Кирон', 'TIVOLI': 'Тиволи',
    'MUSSO': 'Мусо', 'KORANDO': 'Корандо',
    'D-MAX': 'Ди-Макс', 'MU-X': 'Му-Икс',
    'NEXIA': 'Нексия', 'MATIZ': 'Матиз', 'GENTRA': 'Джентра', 'LACETTI': 'Лачетти',
    'TIAGO': 'Тиаго', 'NEXON': 'Нексон', 'HARRIER': 'Харриер', 'SAFARI': 'Сафари',
    'TIAGO EV': 'Тиаго ИВи', 'NEXON EV': 'Нексон ИВи',
    'TERIOS': 'Териос', 'SIRION': 'Сирион', 'MIRA': 'Мира', 'CUORE': 'Куоре',
    '75': '75', '45': '45', '25': '25',
    'H6': 'Х6', 'H9': 'Х9', 'JOLION': 'Жолион', 'DARGO': 'Дарго', 'F7': 'Ф7', 'M6': 'М6',
    'COOLRAY': 'Кулрей', 'ATLAS': 'Атлас', 'EMGRAND': 'Эмгранд', 'TUGELLA': 'Тугелла',
    'MONJARO': 'Монжаро', 'GEOMETRY C': 'Геометри С', 'GEOMETRY A': 'Геометри А',
    'TIGGO 7': 'Тигго 7', 'TIGGO 8': 'Тигго 8', 'ARRIZO 6': 'Арризо 6',
    'TIGGO 4': 'Тигго 4', 'EXEED TXL': 'Эксид ТИксЭл',
    'SONG PLUS': 'Сонг Плюс', 'HAN': 'Хан', 'TANG': 'Танг', 'QIN': 'Кин',
    'DOLPHIN': 'Долфин', 'SEAL': 'Сиил', 'YUAN': 'Юань', 'E2': 'И 2',
    'ATTO 3': 'Атто 3', 'SEAGULL': 'Сигал',
    'CS35': 'СиЭс 35', 'CS55': 'СиЭс 55', 'CS75': 'СиЭс 75', 'UNI-K': 'Юни-Кей',
    'UNI-V': 'Юни-Ви', 'UNI-T': 'Юни-Ти', 'ALSVIN': 'Алсвин', 'BENNI': 'Бенни',
    'WINGLE 5': 'Вингл 5', 'POER': 'Поер',
    'RX': 'АрИкс', 'NX': 'ЭнИкс', 'ES': 'ИЭс', 'LX': 'ЭлИкс', 'IS': 'АйЭс',
    'LS': 'ЭлЭс', 'UX': 'ЮИкс', 'LC': 'ЭлСи', 'RC': 'АрСи',
    'FORESTER': 'Форестер', 'OUTBACK': 'Аутбэк', 'IMPREZA': 'Импреза',
    'LEGACY': 'Легаси', 'XV': 'ИКСиВи', 'BRZ': 'БиАрЗет',
    'CR-V': 'СиАр-Ви', 'CIVIC': 'Сивик', 'ACCORD': 'Аккорд', 'PILOT': 'Пайлот',
    'HR-V': 'ЭйчАр-Ви', 'FIT': 'Фит', 'ODYSSEY': 'Одиссей',
    'VITARA': 'Витара', 'SX4': 'ЭсИкс 4', 'JIMNY': 'Джимни', 'SWIFT': 'Свифт',
    'BALENO': 'Балено', 'CIAZ': 'Сиаз', 'XL7': 'ИКСиЭл 7',
    'ASTRA': 'Астра', 'INSIGNIA': 'Инсигния', 'CORSA': 'Корса', 'MOKKA': 'Мокка',
    'GRANDLAND': 'Грандланд', 'ZAFIRA': 'Зафира', 'COMBO': 'Комбо',
    'SUMO': 'Сумо', 'SAFARI STORME': 'Сафари Сторм',
    'PATRIOT': 'Патриот', 'HUNTER': 'Хантер', 'PICKUP': 'Пикап', 'PROFI': 'Профи',
    'PATRIOT SPORT': 'Патриот Спорт',
    'D22': 'Ди 22', 'NP300': 'ЭнПи 300',
    'BRIDGE': 'Бридж', 'CHANCE': 'Чанс',
    'AX7': 'АИкс 7', 'SX6': 'ЭсИкс 6', 'A9': 'А 9', 'H30': 'Эйч 30',
    'BESTUNE T77': 'Бестюн Т77', 'BESTUNE B70': 'Бестюн Б70',
    'HONGQI H9': 'Хонгки Эйч 9', 'HONGQI HS7': 'Хонгки ЭйчЭс 7',
    'J7': 'Джей 7', 'S7': 'Эс 7', 'IEV7S': 'АйИВи 7Эс',
    'X70': 'Икс 70', 'SOLANO': 'Солано', 'SMILY': 'Смайли', 'BREEZ': 'Бриз',
    'GS4': 'ДжиЭс 4', 'GS8': 'ДжиЭс 8', 'GN8': 'ДжиЭн 8', 'GA8': 'ДжиА 8',
    'T600': 'Ти 600', 'Z500': 'Зет 500', 'SR9': 'ЭсАр 9',
    'V5': 'Ви 5', 'H530': 'Эйч 530',    '2101': '2101 (Копейка)', '2106': '2106 (Шестерка)', '2107': '2107 (Семерка)',
    '2105': '2105 (Пятерка)', '2104': '2104 (Четверка)', '2103': '2103 (Тройка)',
    '2110': '2110 (Десятка)', '2114': '2114 (Четырнадцатая)', '2115': '2115 (Пятнадцатая)',
    '2121': '2121 (Нива)', '2131': '2131 (Нива 5-дверная)', 'TRAVELL': 'Тревел', 'ACTIVE': 'Актив',
    'TIGGO 7 PRO': 'Тигго 7 Про', 'TIGGO 7 PRO MAX': 'Тигго 7 Про Макс',
    'TIGGO 8 PRO': 'Тигго 8 Про', 'TIGGO 8 PRO MAX': 'Тигго 8 Про Макс',
    'OMODA C5': 'Омода С5', 'OMODA S5': 'Омода S5', 'JAECOO J7': 'Жако Джей 7',
    'COOLRAY X': 'Кулрей Икс', 'ATLAS PRO': 'Атлас Про', 'MONJARO PRO': 'Монжаро Про',
    'GEOMETRY G6': 'Геометри Джи6', 'GEOMETRY M6': 'Геометри Эм6',
    'H6 HEV': 'Х6 ХЕВ', 'H6 PHEV': 'Х6 ПХЕВ', 'DARGO PRO': 'Дарго Про',
    'F7X': 'Ф7 Икс', 'JOLION S': 'Жолион Эс',
    'SONG PLUS CHAMPION': 'Сонг Плюс Чемпион', 'HAN EV': 'Хан ИВи', 'TANG DM': 'Танг ДМ',
    'SEAL DM-i': 'Сиил ДМ-ай', 'SEAL EV': 'Сиил ИВи',
    'YUAN PLUS': 'Юань Плюс', 'ATTO 3 LONG RANGE': 'Атто 3 Лонг Рейндж',
    'CS75 PLUS': 'СиЭс 75 Плюс', 'UNI-K IDD': 'Юни-Кей АйДиДи',
    'UNI-V RACING': 'Юни-Ви Рейсинг', 'ALSVIN PLUS': 'Алсвин Плюс',

}

popular_models = {
    'SKODA': ['Octavia', 'Fabia', 'Superb', 'Rapid', 'Kodiaq', 'Karoq', 'Scala', 'Kamiq', 'Enyaq', 'Kushaq', 'Slavia'],
    'TOYOTA': ['Camry', 'Corolla', 'RAV4', 'Highlander', 'Land Cruiser', 'Prado', 'Hilux', 'Avalon', 'Prius', 'C-HR', 'Yaris', 'GR Yaris', 'Supra', '86', 'GR86', 'Sienna', 'Venza', 'Crown', 'Mirai', 'bZ4X'],
    'AUDI': ['A3', 'A4', 'A6', 'A8', 'Q3', 'Q5', 'Q7', 'Q8', 'TT', 'R8', 'e-tron', 'RS6', 'RS7', 'RS Q8', 'A5', 'A7', 'Q2', 'Q4 e-tron', 'Q6', 'SQ8'],
    'BMW': ['3 Series', '5 Series', '7 Series', 'X1', 'X3', 'X5', 'X7', 'M3', 'M5', 'M8', 'i3', 'i4', 'i7', 'iX', 'X2', 'X4', 'X6', '2 Series', '4 Series', '8 Series', 'Z4', 'M2', 'M4'],
    'MERCEDES-BENZ': ['C-Class', 'E-Class', 'S-Class', 'GLC', 'GLE', 'GLS', 'A-Class', 'CLA', 'GLA', 'GLB', 'G-Class', 'AMG GT', 'EQS', 'EQE', 'EQB', 'EQA', 'V-Class', 'Sprinter', 'Vito', 'CLS', 'SL'],
    'VOLKSWAGEN': ['Golf', 'Passat', 'Tiguan', 'Polo', 'Jetta', 'Touareg', 'Arteon', 'ID.3', 'ID.4', 'ID.6', 'ID.7', 'T-Roc', 'T-Cross', 'Caddy', 'Transporter', 'Caravelle', 'Multivan', 'Amarok', 'Teramont', 'Taos'],
    'NISSAN': ['Qashqai', 'X-Trail', 'Juke', 'Patrol', 'Terrano', 'Almera', 'GT-R', 'Murano', 'Pathfinder', 'Frontier', 'Navara', 'Note', 'Micra', 'Leaf', 'Ariya', 'Z', 'Skyline'],
    'HYUNDAI': ['Solaris', 'Elantra', 'Tucson', 'Santa Fe', 'Creta', 'Accent', 'Sonata', 'i30', 'i40', 'Kona', 'Palisade', 'Staria', 'Ioniq 5', 'Ioniq 6', 'Genesis G70', 'Genesis G80', 'Genesis G90', 'Venue', 'Bayon'],
    'KIA': ['Rio', 'Cerato', 'Sportage', 'Sorento', 'Optima', 'Stinger', 'Seltos', 'EV6', 'Carnival', 'Niro', 'Soul', 'Picanto', 'Ceed', 'ProCeed', 'Xceed', 'Mohave', 'Borrego'],
    'FORD': ['Focus', 'Fiesta', 'Mondeo', 'Kuga', 'Explorer', 'Mustang', 'F-150', 'Ranger', 'Bronco', 'Maverick', 'Transit', 'EcoSport', 'Edge', 'Escape', 'Expedition', 'Fusion'],
    'RENAULT': ['Logan', 'Sandero', 'Duster', 'Kaptur', 'Arkana', 'Megane', 'Kangoo', 'Trafic', 'Master', 'Twingo', 'Zoe', 'Captur', 'Espace', 'Talisman', 'Koleos', 'Austral'],
    'CHEVROLET': ['Cruze', 'Aveo', 'Orlando', 'Trailblazer', 'Tahoe', 'Camaro', 'Corvette', 'Malibu', 'Express', 'Silverado', 'Suburban', 'Blazer', 'Equinox', 'Traverse', 'Spark', 'Bolt'],
    'MITSUBISHI': ['Lancer', 'Outlander', 'Pajero', 'ASX', 'Eclipse', 'Mirage', 'Delica', 'Attrage', 'Xpander', 'Triton', 'L200'],
    'PEUGEOT': ['208', '308', '3008', '5008', 'Partner', 'Expert', 'Traveller', 'Boxer', '2008', '408', '508', 'Rifter'],
    'MAZDA': ['6', '3', 'CX-5', 'CX-7', 'CX-9', '626', '323', 'RX-8', 'MX-5', 'MPV', 'CX-30', 'CX-60', 'CX-90', 'CX-3', 'CX-50', 'CX-8', '2', '5'],
    'LI AUTO': ['L7', 'L8', 'L9', 'MEGA', 'ONE'],
    'DONGFENG': ['AX7', 'SX6', 'A9', 'H30', 'A60', 'S50', 'Fengxing T5', 'Fengxing SX6'],
    'FAW': ['Bestune T77', 'Bestune B70', 'Hongqi H9', 'Hongqi HS7', 'Hongqi H5', 'Hongqi E-HS9', 'Bestune T99', 'Bestune NAT'],
    'JAC': ['J7', 'S7', 'iEV7S', 'J2', 'J3', 'J4', 'J5', 'J6', 'S2', 'S3', 'S5', 'Refine S4'],
    'LIFAN': ['X70', 'Solano', 'Smily', 'Breez', 'Myway', 'X80', 'Cebrium'],
    'UAZ': ['Patriot', 'Hunter', 'Pickup', 'Profi', 'Patriot Sport'],
    'GAC': ['GS4', 'GS8', 'GN8', 'GA8', 'GA6', 'GS3', 'GS5', 'GS7', 'Emkoo', 'Empow'],
    'ZOTYE': ['T600', 'Z500', 'SR9', 'T700', 'Z700', 'E200', 'T300'],
    'BRILLIANCE': ['V5', 'H530', 'V7', 'H230', 'H330', 'V6'],
    'GREAT WALL': ['Wingle 5', 'Poer', 'Haval H6', 'Haval H9', 'Wingle 7', 'Coolbear', 'Florid', 'Voleex', 'Socool'],
    'LEXUS': ['RX', 'NX', 'ES', 'LX', 'IS', 'LS', 'UX', 'LC', 'RC', 'GX'],
    'SUBARU': ['Forester', 'Outback', 'Impreza', 'Legacy', 'XV', 'BRZ', 'Ascent', 'Solterra', 'Levorg'],
    'HONDA': ['CR-V', 'Civic', 'Accord', 'Pilot', 'HR-V', 'Fit', 'Odyssey', 'City', 'BR-V', 'Brio', 'Stepwgn'],
    'SUZUKI': ['Vitara', 'SX4', 'Jimny', 'Swift', 'Baleno', 'Ciaz', 'XL7', 'Ignis', 'Ertiga', 'Celerio'],
    'OPEL': ['Astra', 'Insignia', 'Corsa', 'Mokka', 'Grandland', 'Zafira', 'Combo', 'Movano', 'Vivaro', 'Crossland'],
    'CITROEN': ['C4', 'C5', 'Berlingo', 'C3', 'DS3', 'DS4', 'DS7', 'Jumper', 'Spacetourer', 'C4 Cactus', 'C4 Picasso'],
    'FIAT': ['Doblo', 'Ducato', 'Panda', '500', 'Tipo', 'Fiorino', 'Fullback', 'Strada', 'Cronos', 'Argo', 'Mobi'],
    'SEAT': ['Leon', 'Ibiza', 'Ateca', 'Arona', 'Tarraco', 'Cupra', 'Alhambra', 'Toledo', 'Altea'],
    'VOLVO': ['XC60', 'XC90', 'S60', 'S90', 'V90', 'V60', 'XC40', 'C40', 'V40', 'S40', 'V70', 'S80'],
    'JEEP': ['Grand Cherokee', 'Cherokee', 'Renegade', 'Compass', 'Wrangler', 'Gladiator', 'Commander', 'Patriot', 'Compass'],
    'LAND ROVER': ['Range Rover', 'Discovery', 'Defender', 'Evoque', 'Velar', 'Sport', 'Freelander'],
    'JAGUAR': ['F-PACE', 'XE', 'XF', 'XJ', 'E-PACE', 'I-PACE', 'F-TYPE'],
    'PORSCHE': ['Cayenne', 'Macan', 'Panamera', '911', 'Taycan', 'Boxster', 'Cayman', '918 Spyder'],
    'TESLA': ['Model 3', 'Model Y', 'Model S', 'Model X', 'Cybertruck', 'Roadster'],
    'MINI': ['Cooper', 'Countryman', 'Clubman', 'Paceman', 'Cabrio', 'Electric'],
    'SMART': ['Fortwo', 'Forfour', 'Roadster', 'Crossblade'],
    'SSANGYONG': ['Rexton', 'Actyon', 'Kyron', 'Tivoli', 'Musso', 'Korando', 'Rodius', 'Stavic'],
    'ISUZU': ['D-Max', 'MU-X', 'D-Max V-Cross', 'Trooper', 'Rodeo', 'Ascender'],
    'DAEWOO': ['Nexia', 'Matiz', 'Gentra', 'Lacetti', 'Leganza', 'Nubira', 'Lanos', 'Magnus'],
    'DAIHATSU': ['Terios', 'Sirion', 'Mira', 'Cuore', 'Move', 'Tanto', 'Copen', 'Materia'],
    'ROVER': ['75', '45', '25', '400', '600', '800'],
    'TATA': ['Tiago', 'Nexon', 'Harrier', 'Safari', 'Tiago EV', 'Nexon EV', 'Altroz', 'Punch', 'Hexa'],
    'MAHINDRA': ['Scorpio', 'XUV500', 'XUV700', 'Thar', 'Bolero', 'KUV100', 'Marazzo'],
    'IVECO': ['Daily', 'Eurocargo', 'Stralis', 'Trakker'],
    'SCANIA': ['R-series', 'G-series', 'S-series', 'P-series'],
    'KENWORTH': ['T680', 'T880', 'W900', 'C500'],
    'PETERBILT': ['389', '579', '567', '520'],
    'МОСКВИЧ': ['Moskvich 3', 'Moskvich 6', '412', '2140', '2138', '2335'],
    'ЗАЗ': ['Vida', 'Forza', 'Tavria', 'Slavuta', 'Chance', 'Sens'],
    'ГАЗ': ['Gazelle', 'Sobol', 'Valdai', 'Gazelle Next', 'Sobol Business', '3302', '3102', '3110', '31105'],
    'ЖИГУЛИ': ['2101', '2106', '2107', '2105', '2104', '2103'],
    'LADA': ['Granta', 'Vesta', 'XRAY', 'Largus', 'Niva', '4x4', 'Priora', 'Kalina', 'Samara',
             '2101', '2106', '2107', '2105', '2104', '2103', '2110', '2114', '2115', '2121',
             '2131', 'Niva Travel', 'Niva Legend', 'Vesta SW', 'Granta Sport', 'Vesta Sport',
             'Largus Cross', 'XRAY Cross'],
    'CHERY': ['Tiggo 7', 'Tiggo 8', 'Arrizo 6', 'Tiggo 4', 'Exeed TXL', 'Tiggo 3', 'Tiggo 5',
              'Arrizo 5', 'Arrizo 8', 'OMODA C5', 'OMODA S5', 'Jaecoo J7', 'Tiggo 7 Pro',
              'Tiggo 7 Pro Max', 'Tiggo 8 Pro', 'Tiggo 8 Pro Max', 'Arrizo 5 Plus', 'Arrizo 8 Pro'],
    'GEELY': ['Coolray', 'Atlas', 'Emgrand', 'Tugella', 'Monjaro', 'Geometry C', 'Geometry A',
              'Boyue', 'Xingyue', 'Xingyue L', 'Binrui', 'Binyue', 'Haoyue', 'Coolray X',
              'Atlas Pro', 'Monjaro Pro', 'Emgrand L', 'Geometry G6', 'Geometry M6'],
    'BYD': ['Song Plus', 'Han', 'Tang', 'Qin', 'Dolphin', 'Seal', 'Yuan', 'E2', 'Atto 3',
            'Seagull', 'F3', 'S7', 'Yuan Pro', 'Song Pro', 'Destroyer 05', 'Song Plus Champion',
            'Han EV', 'Tang DM', 'Seal DM-i', 'Seal EV', 'Yuan Plus', 'Atto 3 Long Range'],
    'CHANGAN': ['CS35', 'CS55', 'CS75', 'UNI-K', 'UNI-V', 'UNI-T', 'Alsvin', 'Benni', 'Eado',
                'Raeton', 'Hunter', 'CS75 Plus', 'UNI-K IDD', 'UNI-V Racing', 'Alsvin Plus',
                'CS55 Plus', 'CS85', 'CS95', 'Eado Plus'],
    'EXEED': ['TXL', 'LX', 'VX', 'RX', 'TXL Pro', 'LX Plus',
              'VX Pro', 'RX Max'],
    'OMODA': ['C5', 'S5', 'C5 Pro', 'S5 GT', 'C5 Cross', 'S5 Sport'],
    'JAECOO': ['J7', 'J8', 'J7 Pro', 'J8 Max'],
    'MOSKVICH': ['Moskvich 3', 'Moskvich 6', '412', '2140', '2138', '2335', '2141', '2142'],
    'FOTON': ['Tunland', 'Sauvana', 'Gratour', 'Aumark', 'Midi', 'View', 'Tunland G7'],
    'JMC': ['Vigus', 'Baodian', 'Yuhu', 'Reign', 'Grand Avenue'],
    'DFSK': ['Glory', 'Fengguang', 'K01', 'K07', 'C31', 'C32'],
    'DAYUN': ['N7', 'V7', 'H9', 'Light Truck', 'Heavy Truck'],
    'ZX AUTO': ['Grand Tiger', 'Landmark', 'Admiral', 'Terralord'],
}

ENGLISH_NAMES = {v.upper(): k for k, v in RUSSIAN_NAMES.items()}
ENGLISH_MODELS = {v.upper(): k for k, v in RUSSIAN_MODELS.items()}

_brands_cache = None
_models_cache = {}
_cache_time = {}
CACHE_TTL = 300


def normalize_for_search(text: str) -> str:
    text = re.sub(r'[^\w\s-]', '', text.strip().upper())
    text = re.sub(r'\s+', ' ', text)
    return text


def translate_brand(brand: str, to_english: bool = True) -> str:
    brand_norm = normalize_for_search(brand)
    if brand_norm in ['LADA', 'ЛАДА', 'VAZ', 'ВАЗ']:
        return "Lada"
    if to_english:
        return ENGLISH_NAMES.get(brand_norm, brand)
    else:
        return RUSSIAN_NAMES.get(brand_norm, brand)


def translate_model(model: str, to_english: bool = True) -> str:
    model_norm = normalize_for_search(model)
    if to_english:
        return ENGLISH_MODELS.get(model_norm, model)
    else:
        return RUSSIAN_MODELS.get(model_norm, model)


async def get_all_car_brands() -> List[str]:
    try:
        url = 'https://vpic.nhtsa.dot.gov/api/vehicles/GetAllMakes?format=json'
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=3) as response:
                data = await response.json()
                api_brands = [make['Make_Name'].strip() for make in data['Results']]
    except Exception as e:
        print(e)
        api_brands = []

    all_brands = POPULAR_BRANDS.copy()
    for brand in POPULAR_BRANDS:
        russian_name = translate_brand(brand, to_english=False)
        if russian_name != brand and russian_name not in all_brands:
            all_brands.append(russian_name)

    for brand in api_brands:
        if brand not in all_brands:
            all_brands.append(brand)

    return all_brands


async def get_all_car_brands_cached() -> List[str]:
    global _brands_cache, _cache_time
    current_time = asyncio.get_event_loop().time()
    if (_brands_cache is None or 'brands' not in _cache_time or
        current_time - _cache_time.get('brands', 0) > CACHE_TTL):
        _brands_cache = await get_all_car_brands()
        _cache_time['brands'] = current_time
    return _brands_cache


async def get_models_for_brand(brand: str) -> List[str]:
    brand_norm = normalize_for_search(brand)
    if brand_norm in ['LADA', 'ЛАДА', 'VAZ', 'ВАЗ']:
        return ['Granta', 'Vesta', 'XRAY', 'Largus', 'Niva', '4x4',
                'Priora', 'Kalina', 'Samara', '2101', '2106', '2107',
                '2109', '2110', '2114', 'Granta FL', 'Vesta SW',
                'Niva Travel', 'Niva Legend']

    brand_for_api = translate_brand(brand, to_english=True)

    brand_upper = brand_for_api.upper()
    if brand_upper == 'VAZ':
        brand_upper = 'LADA'

    if brand_upper in popular_models:
        return popular_models[brand_upper]

    try:
        url = f'https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMake/{brand_for_api}?format=json'
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=3) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'Results' in data and data['Results']:
                        models = list(set([
                            model['Model_Name'].strip()
                            for model in data['Results']
                        ]))
                        models.sort()
                        return models[:20]
    except Exception as e:
        print(e)

    return []


async def get_models_for_brand_cached(brand: str) -> List[str]:
    global _models_cache, _cache_time
    current_time = asyncio.get_event_loop().time()
    cache_key = normalize_for_search(translate_brand(brand, to_english=True))
    if (cache_key not in _models_cache or cache_key not in _cache_time or
        current_time - _cache_time.get(cache_key, 0) > CACHE_TTL):
        _models_cache[cache_key] = await get_models_for_brand(brand)
        _cache_time[cache_key] = current_time
    return _models_cache.get(cache_key, [])


def parse_car_input(text: str) -> Tuple[Optional[str], Optional[str]]:
    text = text.strip()
    if not text:
        return None, None
    words = text.split()
    if len(words) >= 2:
        return words[0], ' '.join(words[1:])
    return None, None


async def find_brand_suggestions(brand_input: str) -> List[str]:
    all_brands = await get_all_car_brands_cached()
    brand_norm = normalize_for_search(brand_input)
    suggestions = []

    for brand in all_brands:
        if normalize_for_search(brand) == brand_norm:
            suggestions.append(brand)

    if suggestions:
        return suggestions[:5]

    if brand_norm in ['LADA', 'ЛАДА', 'VAZ', 'ВАЗ']:
        return ["Lada", "Lada Granta", "Lada Vesta", "Lada XRAY", "Lada Niva"]

    for brand in POPULAR_BRANDS:
        brand_normed = normalize_for_search(brand)
        if (brand_norm in brand_normed or brand_normed in brand_norm or
            fuzz.ratio(brand_norm, brand_normed) > 60):
            if brand not in suggestions:
                suggestions.append(brand)
            russian_name = translate_brand(brand, to_english=False)
            if russian_name != brand and russian_name not in suggestions:
                suggestions.append(russian_name)
            if len(suggestions) >= 5:
                break

    if len(suggestions) < 5:
        results = process.extract(
            brand_input,
            all_brands,
            scorer=fuzz.partial_ratio,
            limit=5
        )
        for result in results:
            if len(result) >= 2:
                brand = result[0]
                if brand not in suggestions:
                    suggestions.append(brand)
                    if len(suggestions) >= 5:
                        break

    return suggestions[:5] if suggestions else []


async def validate_car_name(input_text: str) -> Tuple[bool, str, List[str]]:
    try:
        brand, model = parse_car_input(input_text)
        if not brand:
            return False, "Введите в формате: Марка Модель", []

        brand_norm = normalize_for_search(brand)
        brand_suggestions = await find_brand_suggestions(brand)
        if not brand_suggestions:
            return False, f"Марка '{brand}' не найдена", []

        exact_match = None
        for suggestion in brand_suggestions:
            if normalize_for_search(suggestion) == brand_norm:
                exact_match = suggestion
                break

        if not exact_match:
            return False, f"Марка '{brand}' не найдена", brand_suggestions

        if model:
            models = await get_models_for_brand_cached(exact_match)
            if models:
                model_english = translate_model(model, to_english=True)
                model_norm = normalize_for_search(model_english)
                found_model = None
                for m in models:
                    if normalize_for_search(m) == model_norm:
                        found_model = m
                        break

                if found_model:
                    final_name = f"{exact_match} {found_model}"
                    return True, final_name, []

                model_suggestions = []
                for m in models[:5]:
                    model_russian = translate_model(m, to_english=False)
                    model_suggestions.append(f"{exact_match} {m}")
                    if model_russian != m:
                        brand_russian = translate_brand(exact_match, to_english=False)
                        model_suggestions.append(f"{brand_russian} {model_russian}")

                unique_suggestions = []
                for suggestion in model_suggestions:
                    if suggestion not in unique_suggestions:
                        unique_suggestions.append(suggestion)
                    if len(unique_suggestions) >= 5:
                        break

                if unique_suggestions:
                    return False, f"Модель '{model}' не найдена", unique_suggestions

        return True, exact_match, []

    except Exception as e:
        print(f"Ошибка в validate_car_name: {e}")
        return False, "Произошла ошибка при проверке названия", []