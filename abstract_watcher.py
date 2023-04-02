import abc
from typing import Coroutine, Any
import asyncio

"""
Описание задачи:
    Необходимо реализовать планировщик, позволяющий запускать и отслеживать фоновые корутины.
    Планировщик должен обеспечивать:
        - возможность планирования новой задачи
        - отслеживание состояния завершенных задач (сохранение результатов их выполнения)
        - отмену незавершенных задач перед остановкой работы планировщика
        
    Ниже представлен интерфейс, которому должна соответствовать ваша реализация.
    
    Обратите внимание, что перед завершением работы планировщика, все запущенные им корутины должны быть
    корректным образом завершены.
    
    В папке tests вы найдете тесты, с помощью которых мы будем проверять работоспособность вашей реализации
    
"""


class AbstractRegistrator(abc.ABC):
    """
    Сохраняет результаты работы завершенных задач.
    В тестах мы передадим в ваш Watcher нашу реализацию Registrator и проверим корректность сохранения результатов.
    """

    @abc.abstractmethod
    def register_value(self, value: Any) -> None:
        # Store values returned from done task
        ...

    @abc.abstractmethod
    def register_error(self, error: BaseException) -> None:
        # Store exceptions returned from done task
        ...


class AbstractWatcher(abc.ABC):
    """
    Абстрактный интерфейс, которому должна соответсововать ваша реализация Watcher.
    При тестировании мы расчитываем на то, что этот интерфейс будет соблюден.
    """

    def __init__(self, registrator: AbstractRegistrator):
        self.registrator = registrator  # we expect to find registrator here

    @abc.abstractmethod
    async def start(self) -> None:
        # Good idea is to implement here all necessary for start watcher :)
        ...

    @abc.abstractmethod
    async def stop(self) -> None:
        # Method will be called on the end of the Watcher's work
        ...

    @abc.abstractmethod
    def start_and_watch(self, coro: Coroutine) -> None:
        # Start new task and put to watching
        ...


class StudentWatcher(AbstractWatcher):
    def __init__(self, registrator: AbstractRegistrator,
                 timeout: float = None):
        super().__init__(registrator)
        self.timeout = timeout
        self.__is_running = False
        self.tasks = []

    @property
    def is_running(self):
        return self.__is_running

    def __register_task(self, task: asyncio.Task):
        if task.exception() is not None:
            self.registrator.register_error(task.exception())
        else:
            self.registrator.register_value(task.result())

    async def start(self) -> None:
        if self.__is_running:
            raise RuntimeError('Watcher is already running')
        self.__is_running = True

    async def stop(self) -> None:
        # We can't cancel all pending tasks here, because there is no
        # delay of any kind in given tests, we will just cancel all tasks
        # before complition.
        #
        # So there should be some kind of asynchronous await, but:
        # 1. Instruction implies that there is a case in which StudentWatcher
        #    should cancel unfinished tasks
        # 2. There is no information about task estimated duration, so
        #    we can't calculate timeout
        #
        # There is only one solution I can find - use asyncio.wait with timeout
        # which we can define in StudentWatcher constructor manualy.
        if not self.__is_running:
            raise RuntimeError('Watcher is not running')
        done, pending = await asyncio.wait(self.tasks, timeout=self.timeout)
        for task in done:
            self.__register_task(task)
        for task in pending:
            task.cancel()
        self.tasks = []
        self.__is_running = False

    def start_and_watch(self, coro: Coroutine) -> None:
        if not self.__is_running:
            raise RuntimeError('Watcher is not running')
        task = asyncio.create_task(coro)
        self.tasks.append(task)
