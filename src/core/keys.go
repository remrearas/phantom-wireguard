package core

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/hex"
	"fmt"

	"golang.org/x/crypto/curve25519"
)

// GeneratePrivateKey creates a new Curve25519 private key with clamping.
// Returns hex-encoded 64-char string.
func GeneratePrivateKey() (string, error) {
	var key [32]byte
	if _, err := rand.Read(key[:]); err != nil {
		return "", fmt.Errorf("random read: %w", err)
	}
	key[0] &= 248
	key[31] &= 127
	key[31] |= 64
	return hex.EncodeToString(key[:]), nil
}

// DerivePublicKey derives a Curve25519 public key from a hex-encoded private key.
// Returns hex-encoded 64-char string.
func DerivePublicKey(privHex string) (string, error) {
	privBytes, err := hex.DecodeString(privHex)
	if err != nil || len(privBytes) != 32 {
		return "", fmt.Errorf("invalid private key hex")
	}
	pubBytes, err := curve25519.X25519(privBytes, curve25519.Basepoint)
	if err != nil {
		return "", fmt.Errorf("x25519: %w", err)
	}
	return hex.EncodeToString(pubBytes), nil
}

// GeneratePresharedKey creates a random 32-byte preshared key.
// Returns hex-encoded 64-char string.
func GeneratePresharedKey() (string, error) {
	var key [32]byte
	if _, err := rand.Read(key[:]); err != nil {
		return "", fmt.Errorf("random read: %w", err)
	}
	return hex.EncodeToString(key[:]), nil
}

// HexToBase64 converts a hex-encoded key to base64 (WireGuard config format).
func HexToBase64(hexStr string) (string, error) {
	b, err := hex.DecodeString(hexStr)
	if err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(b), nil
}
