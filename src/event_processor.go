/*
 * ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
 * ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
 * ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
 * ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
 * ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
 * ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
 *
 * Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
 * Licensed under AGPL-3.0 - see LICENSE file for details
 */

package main

import (
	"fmt"
	"io"
	"os"
)

const logPrefix = "[compose-bridge]"

// bridgeEventProcessor logs Compose lifecycle events to an io.Writer.
type bridgeEventProcessor struct {
	out io.Writer
}

// newBridgeEventProcessor creates a processor that writes to stderr.
func newBridgeEventProcessor() *bridgeEventProcessor {
	return &bridgeEventProcessor{out: os.Stderr}
}

// OperationStart logs the beginning of a compose operation.
func (p *bridgeEventProcessor) OperationStart(op string) {
	fmt.Fprintf(p.out, "%s START: %s\n", logPrefix, op)
}

// OperationEnd logs the completion of a compose operation.
func (p *bridgeEventProcessor) OperationEnd(op string, err error) {
	if err != nil {
		fmt.Fprintf(p.out, "%s DONE: %s (error: %v)\n", logPrefix, op, err)
	} else {
		fmt.Fprintf(p.out, "%s DONE: %s (success)\n", logPrefix, op)
	}
}
