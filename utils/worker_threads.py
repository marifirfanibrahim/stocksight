"""
worker threads module
handles background processing for pyqt
keeps ui responsive during long operations
"""

from PyQt5.QtCore import QObject, QRunnable, QThread, pyqtSignal, pyqtSlot
from typing import Any, Callable, Tuple
import traceback
import sys
import inspect


# ============================================================================
#                             WORKER SIGNALS
# ============================================================================

class WorkerSignals(QObject):
    # signals for worker thread communication
    
    started = pyqtSignal()
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    progress_text = pyqtSignal(str)
    progress_detail = pyqtSignal(int, str)


# ============================================================================
#                             WORKER RUNNABLE
# ============================================================================

class WorkerRunnable(QRunnable):
    # worker runnable for thread pool execution
    
    def __init__(self, fn: Callable, *args, **kwargs):
        # initialize with function and arguments
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.is_cancelled = False
    
    @pyqtSlot()
    def run(self):
        # execute function in thread pool
        self.signals.started.emit()
        
        try:
            # add progress callback if function accepts it
            if self._accepts_progress_callback():
                self.kwargs["progress_callback"] = self._progress_callback
            
            result = self.fn(*self.args, **self.kwargs)
            
        except Exception as e:
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
    
    def _accepts_progress_callback(self) -> bool:
        # check if function accepts progress callback
        try:
            sig = inspect.signature(self.fn)
            return "progress_callback" in sig.parameters
        except Exception:
            return False
    
    def _progress_callback(self, value: int, text: str = ""):
        # emit progress signal
        if self.is_cancelled:
            raise InterruptedError("operation cancelled")
        # support either (value) or (value, text) callers
        if isinstance(value, (list, tuple)) and len(value) >= 1:
            # defensive: handle a single iterable passed accidentally
            value = value[0]

        self.signals.progress.emit(int(value))
        if text:
            self.signals.progress_text.emit(text)
    
    def cancel(self):
        # request cancellation
        self.is_cancelled = True


# ============================================================================
#                              WORKER THREAD
# ============================================================================

class WorkerThread(QThread):
    # worker thread for long running operations
    
    started_signal = pyqtSignal()
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    result_signal = pyqtSignal(object)
    progress_signal = pyqtSignal(int)
    progress_text_signal = pyqtSignal(str)
    
    def __init__(self, fn: Callable, *args, **kwargs):
        # initialize with function and arguments
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.is_cancelled = False
        self.result = None
    
    def run(self):
        # execute function in thread
        self.started_signal.emit()
        
        try:
            # only add progress callback if function accepts it
            if self._accepts_progress_callback():
                self.kwargs["progress_callback"] = self._progress_callback
            
            self.result = self.fn(*self.args, **self.kwargs)
            self.result_signal.emit(self.result)
            
        except InterruptedError:
            self.error_signal.emit("operation cancelled")
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()
    
    def _accepts_progress_callback(self) -> bool:
        # check if function accepts progress callback parameter
        try:
            sig = inspect.signature(self.fn)
            return "progress_callback" in sig.parameters
        except (ValueError, TypeError):
            # some built-in functions don't support signature inspection
            return False
    
    def _progress_callback(self, value: int, text: str = ""):
        # emit progress signals
        if self.is_cancelled:
            raise InterruptedError("operation cancelled")
        # support either (value) or (value, text) callers
        if isinstance(value, (list, tuple)) and len(value) >= 1:
            value = value[0]

        self.progress_signal.emit(int(value))
        if text:
            self.progress_text_signal.emit(text)
    
    def cancel(self):
        # request thread cancellation
        self.is_cancelled = True


# ============================================================================
#                           BATCH WORKER
# ============================================================================

class BatchWorker(QThread):
    # worker for processing items in batch
    
    started_signal = pyqtSignal()
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    result_signal = pyqtSignal(object)
    progress_signal = pyqtSignal(int, str)
    item_completed_signal = pyqtSignal(str, object)
    
    def __init__(self, items: list, process_fn: Callable):
        # initialize with items and processing function
        super().__init__()
        self.items = items
        self.process_fn = process_fn
        self.is_cancelled = False
        self.results = {}
    
    def run(self):
        # process all items
        self.started_signal.emit()
        
        try:
            total = len(self.items)
            
            for i, item in enumerate(self.items):
                if self.is_cancelled:
                    raise InterruptedError("operation cancelled")
                
                # process item
                result = self.process_fn(item)
                self.results[item] = result
                
                # emit progress
                progress = int((i + 1) / total * 100)
                self.progress_signal.emit(progress, str(item))
                self.item_completed_signal.emit(str(item), result)
            
            self.result_signal.emit(self.results)
            
        except InterruptedError:
            self.error_signal.emit("operation cancelled")
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()
    
    def cancel(self):
        # request cancellation
        self.is_cancelled = True


# ============================================================================
#                         SIMPLE WORKER
# ============================================================================

class SimpleWorker(QThread):
    # simple worker that never injects progress callback
    
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    result_signal = pyqtSignal(object)
    
    def __init__(self, fn: Callable, *args, **kwargs):
        # initialize with function and arguments
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.result = None
    
    def run(self):
        # execute function in thread
        try:
            self.result = self.fn(*self.args, **self.kwargs)
            self.result_signal.emit(self.result)
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()