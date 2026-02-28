package bridge

import (
	"fmt"
	"sync"
	"unsafe"

	"golang.zx2c4.com/wireguard/device"
)

// LogCallback is a C-compatible function pointer for receiving log messages.
// level: 1=ERROR, 2=VERBOSE
// msg: null-terminated C string (caller must NOT free)
type LogCallback func(level int32, msg *byte, context unsafe.Pointer)

var (
	logCallbackFn  LogCallback
	logCallbackCtx unsafe.Pointer
	logCallbackMu  sync.RWMutex
)

// SetLogCallback registers a callback for all bridge log output.
// Pass nil to disable callback and revert to silent logging.
func SetLogCallback(fn LogCallback, ctx unsafe.Pointer) {
	logCallbackMu.Lock()
	defer logCallbackMu.Unlock()
	logCallbackFn = fn
	logCallbackCtx = ctx
}

// newCallbackLogger creates a wireguard-go Logger that routes through
// the registered callback. If no callback is set, logs are discarded.
func newCallbackLogger(level int, prepend string) *device.Logger {
	logger := &device.Logger{
		Verbosef: device.DiscardLogf,
		Errorf:   device.DiscardLogf,
	}

	if level >= device.LogLevelError {
		logger.Errorf = func(format string, args ...any) {
			msg := fmt.Sprintf(prepend+format, args...)
			emitLog(1, msg)
		}
	}
	if level >= device.LogLevelVerbose {
		logger.Verbosef = func(format string, args ...any) {
			msg := fmt.Sprintf(prepend+format, args...)
			emitLog(2, msg)
		}
	}

	return logger
}

// emitLog sends a log message through the callback if registered.
func emitLog(level int32, msg string) {
	logCallbackMu.RLock()
	fn := logCallbackFn
	ctx := logCallbackCtx
	logCallbackMu.RUnlock()

	if fn == nil {
		return
	}

	// Convert to null-terminated byte slice for C compatibility
	buf := make([]byte, len(msg)+1)
	copy(buf, msg)
	buf[len(msg)] = 0

	fn(level, &buf[0], ctx)
}
