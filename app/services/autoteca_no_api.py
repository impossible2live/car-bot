from playwright.async_api import async_playwright
import asyncio
import json
from pathlib import Path
import logging
import os
import re
from app.config import AUTOTEKA_EMAIL, AUTOTEKA_PASSWORD

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if not AUTOTEKA_EMAIL or not AUTOTEKA_PASSWORD:
    logger.warning("Не указаны учетные данные для Autoteka в переменных окружения")
    logger.warning("Установите переменные: AUTOTEKA_EMAIL и AUTOTEKA_PASSWORD")


class AutotekaService:
    def __init__(self, email: str = None, password: str = None):
        self.email = email or AUTOTEKA_EMAIL
        self.password = password or AUTOTEKA_PASSWORD
        if not self.email or not self.password:
            raise ValueError("Не указаны учетные данные для Autoteka")
        self.cookies_file = Path("autoteka_cookies.json")
        logger.info(f"Инициализирован сервис Autoteka")

    async def _save_cookies(self, context):
        cookies = await context.cookies()
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f)
        logger.debug("Куки сохранены")

    async def _load_cookies(self, context) -> bool:
        if self.cookies_file.exists():
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)
                logger.debug("Куки загружены")
                return True
        return False

    async def _login(self, page):
        logger.info("Выполняем вход в Autoteka")
        try:
            await page.click('[data-marker="auth-button"]')
            await page.wait_for_timeout(1500)
            await page.wait_for_selector('[data-marker="auth-modal/popup"]', timeout=5000)
            logger.info("Модальное окно авторизации открыто")
            await page.wait_for_selector('[data-marker="sign-in-with-password-button"]', timeout=5000)
            await page.click('[data-marker="sign-in-with-password-button"]')
            await page.wait_for_timeout(1000)
            await page.fill('[data-marker="email"] input', self.email)
            await page.fill('[data-marker="password"] input', self.password)
            await page.wait_for_timeout(500)
            await page.press('[data-marker="password"] input', 'Enter')
            await page.wait_for_timeout(3000)
            logger.info("Успешно вошли в аккаунт")
        except Exception as e:
            logger.error(f"Ошибка при входе: {e}")
            await page.screenshot(path="login_error.png")
            raise

    async def get_remaining_reports_count(self) -> int:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()
            try:
                has_cookies = await self._load_cookies(context)
                await page.goto("https://autoteka.ru")
                await page.wait_for_timeout(2000)
                if not has_cookies:
                    await self._login(page)
                    await self._save_cookies(context)
                await page.goto("https://autoteka.ru/reports")
                await page.wait_for_timeout(3000)
                content = await page.content()
                match = re.search(r'Осталось\s+(\d+)\s+проверок', content)
                if match:
                    count = int(match.group(1))
                    logger.info(f"Осталось проверок: {count}")
                    return count
                else:
                    logger.warning("Не удалось найти количество оставшихся проверок")
                    return 0
            except Exception as e:
                logger.error(f"Ошибка при получении количества отчетов: {e}")
                return 0
            finally:
                await browser.close()

    async def _check_page_content(self, page, vin: str, license_plate: str = None):
        await page.wait_for_timeout(3000)
        page_text = (await page.content()).lower()
        if 'скачать pdf' in page_text:
            return 'pdf_available', 'PDF доступен для скачивания'
        if 'данных для формирования отчёта по указанному vin недостаточно' in page_text:
            return 'no_vin_data', 'Нет данных по VIN'
        if license_plate and 'данных для формирования отчёта по указанному госномеру недостаточно' in page_text:
            return 'no_plate_data', 'Нет данных по госномеру'
        if 'выберите пакет и получите подробный отчёт' in page_text:
            return 'no_balance', 'Нет отчетов на балансе'
        payment_phrases = ['оплатите отчёт', 'купить отчёт', 'приобрести отчёт']
        for phrase in payment_phrases:
            if phrase in page_text:
                return 'no_balance', 'Необходима оплата отчета'
        report_phrases = ['отчёт об истории авто', 'отчет готов', 'история автомобиля']
        for phrase in report_phrases:
            if phrase in page_text:
                return 'pdf_available', 'Отчет доступен'
        return 'unknown', 'Неизвестный статус страницы'

    async def _search_and_check(self, page, search_value: str, is_license_plate: bool = False):
        search_input = await page.query_selector('[data-marker="input"]')
        await search_input.click(click_count=3)
        await search_input.press('Delete')
        await search_input.fill(search_value)
        await page.wait_for_timeout(500)
        await page.click('form[data-marker="search-form"] [data-marker="submit"]')
        logger.info(f"Поиск {'по госномеру' if is_license_plate else 'по VIN'}: {search_value}")
        await page.wait_for_timeout(5000)
        return await self._check_page_content(page, search_value if not is_license_plate else None,
                                              search_value if is_license_plate else None)

    async def _download_pdf(self, page, identifier: str) -> str:
        download_selectors = [
            'a:has-text("Скачать PDF")',
            'button:has-text("Скачать PDF")',
            'a:has-text("PDF")',
            'button:has-text("PDF")',
            'a[href$=".pdf"]'
        ]
        for selector in download_selectors:
            elements = await page.query_selector_all(selector)
            for elem in elements:
                if await elem.is_visible():
                    try:
                        async with page.expect_download(timeout=10000) as download_info:
                            await elem.click()
                        download = await download_info.value
                        filename = f"autoteka_{identifier}.pdf"
                        filepath = os.path.join("reports", filename)
                        await download.save_as(filepath)
                        logger.info(f"PDF скачан: {filepath}")
                        return filepath
                    except Exception as e:
                        logger.warning(f"Не удалось скачать через {selector}: {e}")
                        continue
        html_filename = f"autoteka_{identifier}.html"
        html_content = await page.content()
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"PDF не найден, сохранен HTML: {html_filename}")
        return html_filename

    async def get_vehicle_report(self, vin: str, license_plate: str) -> str:
        logger.info(f"Запрос отчета: VIN={vin}, госномер={license_plate}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()
            try:
                has_cookies = await self._load_cookies(context)
                await page.goto("https://autoteka.ru")
                await page.wait_for_timeout(2000)
                if not has_cookies:
                    await self._login(page)
                    await self._save_cookies(context)
                logger.info("Пробуем поиск по VIN...")
                status, message = await self._search_and_check(page, vin, is_license_plate=False)
                logger.info(f"Статус по VIN: {message}")
                if status == 'pdf_available':
                    file_path = await self._download_pdf(page, f"vin_{vin}")
                    return file_path
                elif status == 'no_vin_data':
                    logger.info("Нет данных по VIN, пробуем госномер...")
                    status2, message2 = await self._search_and_check(page, license_plate, is_license_plate=True)
                    logger.info(f"Статус по госномеру: {message2}")
                    if status2 == 'pdf_available':
                        file_path = await self._download_pdf(page, f"plate_{license_plate}")
                        return file_path
                    elif status2 == 'no_plate_data':
                        raise Exception("Автотека: невозможно подключить - нет данных ни по VIN, ни по госномеру")
                    elif status2 == 'no_balance':
                        raise Exception("Автотека: нет отчетов на балансе")
                    else:
                        raise Exception(f"Автотека: неизвестный статус при поиске по госномеру - {message2}")
                elif status == 'no_balance':
                    raise Exception("Автотека: нет отчетов на балансе")
                else:
                    raise Exception(f"Автотека: {message}")
            except Exception as e:
                logger.error(f"Ошибка при получении отчета: {e}")
                raise
            finally:
                await browser.close()


async def get_vehicle_report_async(vin: str, license_plate: str, email: str = None, password: str = None) -> str:
    service = AutotekaService(email=email, password=password)
    return await service.get_vehicle_report(vin, license_plate)


async def get_remaining_reports_async(email: str = None, password: str = None) -> int:
    service = AutotekaService(email=email, password=password)
    return await service.get_remaining_reports_count()


async def example_async():
    try:
        remaining = await get_remaining_reports_async()
        print(f"✅ Осталось проверок: {remaining}")

        result = await get_vehicle_report_async(
            vin="XTA210990Y2764399",
            license_plate="А123ВС77"
        )
        print(f"✅ Успех! Файл: {result}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(example_async())