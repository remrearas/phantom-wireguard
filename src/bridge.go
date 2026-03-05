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
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"

	composetypes "github.com/compose-spec/compose-go/v2/types"
	"github.com/docker/cli/cli/command"
	"github.com/docker/cli/cli/flags"
	"github.com/docker/compose/v5/pkg/api"
	"github.com/docker/compose/v5/pkg/compose"
	"github.com/moby/moby/api/pkg/stdcopy"
	moby "github.com/moby/moby/client"
)

// composeBridge wraps the Docker Compose v5 SDK for FFI access.
// One bridge = one compose project. Each instance gets a unique
// project name suffix so it never conflicts with other instances.
type composeBridge struct {
	dockerClient moby.APIClient
	service      api.Compose
	project      *composetypes.Project
	projectName  string
	lastErr      string
	mu           sync.Mutex
}

// detectDockerHost ensures DOCKER_HOST is set when not provided.
// On macOS Docker Desktop, the Go CLI context resolver can crash
// inside a c-shared library if the socket path isn't explicit.
func detectDockerHost() {
	if os.Getenv("DOCKER_HOST") != "" {
		return
	}

	candidates := []string{"/var/run/docker.sock"}
	if runtime.GOOS == "darwin" {
		if home := os.Getenv("HOME"); home != "" {
			candidates = append(candidates, filepath.Join(home, ".docker/run/docker.sock"))
		}
	}

	for _, sock := range candidates {
		if info, err := os.Stat(sock); err == nil && info.Mode().Type() == os.ModeSocket {
			if err := os.Setenv("DOCKER_HOST", "unix://"+sock); err == nil {
				return
			}
		}
	}
}

// shortID returns a 6-char random hex string for project isolation.
func shortID() string {
	b := make([]byte, 3)
	if _, err := rand.Read(b); err != nil {
		return "000000"
	}
	return hex.EncodeToString(b)
}

// newComposeBridge initialises Docker CLI, Compose service, and loads the project.
func newComposeBridge(configPath, projectName string) (*composeBridge, error) {
	detectDockerHost()

	dockerCli, err := command.NewDockerCli()
	if err != nil {
		return nil, fmt.Errorf("docker cli init: %w", err)
	}
	if err := dockerCli.Initialize(&flags.ClientOptions{}); err != nil {
		return nil, fmt.Errorf("docker cli initialize: %w", err)
	}

	svc, err := compose.NewComposeService(dockerCli)
	if err != nil {
		return nil, fmt.Errorf("compose service init: %w", err)
	}

	absPath, err := filepath.Abs(configPath)
	if err != nil {
		return nil, fmt.Errorf("resolve path: %w", err)
	}

	if projectName == "" {
		projectName = filepath.Base(filepath.Dir(absPath))
	}
	projectName = projectName + "-" + shortID()

	ctx := context.Background()
	project, err := svc.LoadProject(ctx, api.ProjectLoadOptions{
		ConfigPaths: []string{absPath},
		ProjectName: projectName,
		WorkingDir:  filepath.Dir(absPath),
	})
	if err != nil {
		return nil, fmt.Errorf("load project: %w", err)
	}

	return &composeBridge{
		dockerClient: dockerCli.Client(),
		service:      svc,
		project:      project,
		projectName:  project.Name,
	}, nil
}

// setError records the last error for GetLastError retrieval.
func (b *composeBridge) setError(err error) {
	if err != nil {
		b.lastErr = err.Error()
	} else {
		b.lastErr = ""
	}
}

// projectUp starts all services.
func (b *composeBridge) projectUp() error {
	b.mu.Lock()
	defer b.mu.Unlock()

	ep := newBridgeEventProcessor()
	ep.OperationStart("up")

	ctx := context.Background()
	err := b.service.Up(ctx, b.project, api.UpOptions{
		Create: api.CreateOptions{
			RemoveOrphans: true,
		},
		Start: api.StartOptions{},
	})

	ep.OperationEnd("up", err)
	return err
}

// projectDown stops and removes services, networks, and volumes.
func (b *composeBridge) projectDown() error {
	b.mu.Lock()
	defer b.mu.Unlock()

	ep := newBridgeEventProcessor()
	ep.OperationStart("down")

	ctx := context.Background()
	err := b.service.Down(ctx, b.projectName, api.DownOptions{
		RemoveOrphans: true,
		Volumes:       true,
	})

	ep.OperationEnd("down", err)
	return err
}

// containerInfo holds container details for ProjectPs JSON output.
type containerInfo struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	Service string `json:"service"`
	State   string `json:"state"`
	Status  string `json:"status"`
}

// projectPs returns a JSON array of container information.
func (b *composeBridge) projectPs() (string, error) {
	b.mu.Lock()
	defer b.mu.Unlock()

	ctx := context.Background()
	containers, err := b.service.Ps(ctx, b.projectName, api.PsOptions{
		All: true,
	})
	if err != nil {
		return "", err
	}

	infos := make([]containerInfo, 0, len(containers))
	for _, c := range containers {
		infos = append(infos, containerInfo{
			ID:      c.ID,
			Name:    c.Name,
			Service: c.Service,
			State:   string(c.State),
			Status:  c.Status,
		})
	}

	data, err := json.Marshal(infos)
	if err != nil {
		return "", fmt.Errorf("json marshal: %w", err)
	}
	return string(data), nil
}

// execResult holds the output of a ServiceExec call.
type execResult struct {
	ExitCode int    `json:"exit_code"`
	Stdout   string `json:"stdout"`
	Stderr   string `json:"stderr"`
}

// findContainerID finds the first container ID for a service via Ps.
func (b *composeBridge) findContainerID(service string) (string, error) {
	ctx := context.Background()
	containers, err := b.service.Ps(ctx, b.projectName, api.PsOptions{All: true})
	if err != nil {
		return "", fmt.Errorf("ps: %w", err)
	}
	for _, c := range containers {
		if c.Service == service {
			return c.ID, nil
		}
	}
	return "", fmt.Errorf("no container found for service %q", service)
}

// serviceExec runs a command inside a service container using Docker API
// directly, capturing stdout and stderr.
func (b *composeBridge) serviceExec(service, cmdJSON, envJSON string) (string, error) {
	b.mu.Lock()
	defer b.mu.Unlock()

	var args []string
	if err := json.Unmarshal([]byte(cmdJSON), &args); err != nil {
		return "", fmt.Errorf("parse command json: %w", err)
	}
	if len(args) == 0 {
		return "", fmt.Errorf("empty command")
	}

	var envVars []string
	if envJSON != "" {
		var envMap map[string]string
		if err := json.Unmarshal([]byte(envJSON), &envMap); err != nil {
			return "", fmt.Errorf("parse env json: %w", err)
		}
		for k, v := range envMap {
			envVars = append(envVars, k+"="+v)
		}
	}

	containerID, err := b.findContainerID(service)
	if err != nil {
		return "", err
	}

	ctx := context.Background()

	// Create exec
	execResp, err := b.dockerClient.ExecCreate(ctx, containerID, moby.ExecCreateOptions{
		Cmd:          args,
		Env:          envVars,
		AttachStdout: true,
		AttachStderr: true,
	})
	if err != nil {
		return "", fmt.Errorf("exec create: %w", err)
	}

	// Attach and capture
	attach, err := b.dockerClient.ExecAttach(ctx, execResp.ID, moby.ExecAttachOptions{})
	if err != nil {
		return "", fmt.Errorf("exec attach: %w", err)
	}
	defer attach.Close()

	// Read multiplexed stdout + stderr
	var stdout, stderr bytes.Buffer
	if _, err := stdcopy.StdCopy(&stdout, &stderr, attach.Reader); err != nil {
		return "", fmt.Errorf("exec read: %w", err)
	}

	// Poll exit code — exec may still be finishing after stream EOF
	var inspect moby.ExecInspectResult
	for range 50 {
		inspect, err = b.dockerClient.ExecInspect(ctx, execResp.ID, moby.ExecInspectOptions{})
		if err != nil {
			return "", fmt.Errorf("exec inspect: %w", err)
		}
		if !inspect.Running {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}

	result := execResult{
		ExitCode: inspect.ExitCode,
		Stdout:   stdout.String(),
		Stderr:   stderr.String(),
	}

	data, err := json.Marshal(result)
	if err != nil {
		return "", fmt.Errorf("json marshal: %w", err)
	}
	return string(data), nil
}

// bridgeLogConsumer implements api.LogConsumer, collecting output into a buffer.
type bridgeLogConsumer struct {
	lines []string
	mu    sync.Mutex
}

func (c *bridgeLogConsumer) Log(_ string, message string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.lines = append(c.lines, message)
}

func (c *bridgeLogConsumer) Err(_ string, message string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.lines = append(c.lines, message)
}

func (c *bridgeLogConsumer) Status(_ string, _ string) {}

func (c *bridgeLogConsumer) String() string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return strings.Join(c.lines, "\n")
}

// serviceLogs retrieves logs from a service.
func (b *composeBridge) serviceLogs(service string, follow bool) (string, error) {
	b.mu.Lock()
	defer b.mu.Unlock()

	consumer := &bridgeLogConsumer{}
	ctx := context.Background()

	err := b.service.Logs(ctx, b.projectName, consumer, api.LogOptions{
		Services: []string{service},
		Follow:   follow,
	})
	if err != nil {
		return "", err
	}

	return consumer.String(), nil
}
