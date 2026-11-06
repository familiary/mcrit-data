// Exerciser for golang.org/x/crypto: the ciphers, hashes, KDFs and key
// exchanges Go malware and Go network tools actually call (ChaCha20 and its
// AEADs, HKDF, SHA-3, BLAKE2, Curve25519, NaCl, the legacy block ciphers, the
// password hashes) and an SSH client/server handshake over an in-memory pipe.
// Built inside the x/crypto module, so every golang.org/x/crypto symbol in
// the image is the library's own.
package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"fmt"
	"net"
	"os"

	"golang.org/x/crypto/argon2"
	"golang.org/x/crypto/bcrypt"
	"golang.org/x/crypto/blake2b"
	"golang.org/x/crypto/blake2s"
	"golang.org/x/crypto/blowfish"
	"golang.org/x/crypto/cast5"
	"golang.org/x/crypto/chacha20"
	"golang.org/x/crypto/chacha20poly1305"
	"golang.org/x/crypto/curve25519"
	"golang.org/x/crypto/hkdf"
	"golang.org/x/crypto/md4"
	"golang.org/x/crypto/nacl/box"
	"golang.org/x/crypto/nacl/secretbox"
	"golang.org/x/crypto/pbkdf2"
	"golang.org/x/crypto/poly1305"
	"golang.org/x/crypto/ripemd160"
	"golang.org/x/crypto/salsa20"
	"golang.org/x/crypto/scrypt"
	"golang.org/x/crypto/sha3"
	"golang.org/x/crypto/ssh"
	"golang.org/x/crypto/tea"
	"golang.org/x/crypto/twofish"
	"golang.org/x/crypto/xtea"
)

func must(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func main() {
	key := make([]byte, 32)
	nonce := make([]byte, 12)
	rand.Read(key)
	rand.Read(nonce)
	msg := []byte("exerciser message")

	// ChaCha20 stream, ChaCha20-Poly1305 and XChaCha20-Poly1305.
	c, err := chacha20.NewUnauthenticatedCipher(key, nonce)
	must(err)
	out := make([]byte, len(msg))
	c.XORKeyStream(out, msg)
	aead, err := chacha20poly1305.New(key)
	must(err)
	sealed := aead.Seal(nil, nonce, msg, nil)
	_, err = aead.Open(nil, nonce, sealed, nil)
	must(err)
	xaead, err := chacha20poly1305.NewX(key)
	must(err)
	xn := make([]byte, chacha20poly1305.NonceSizeX)
	_, err = xaead.Open(nil, xn, xaead.Seal(nil, xn, msg, nil), nil)
	must(err)
	var pk [32]byte
	var tag [16]byte
	copy(pk[:], key)
	poly1305.Sum(&tag, msg, &pk)
	salsa20.XORKeyStream(out, msg, nonce[:8], &pk)

	// Key derivation.
	h := hkdf.New(sha256.New, key, nonce, []byte("info"))
	h.Read(out)
	pbkdf2.Key([]byte("pw"), nonce, 1000, 32, sha256.New)
	scrypt.Key([]byte("pw"), nonce, 1<<10, 8, 1, 32)
	argon2.IDKey([]byte("pw"), nonce, 1, 8*1024, 1, 32)
	bcrypt.GenerateFromPassword([]byte("pw"), bcrypt.MinCost)

	// Hashes.
	k := sha3.New256()
	k.Write(msg)
	sha3.Sum512(msg)
	sha3.NewLegacyKeccak256().Write(msg)
	sha3.NewShake256().Write(msg)
	blake2b.Sum256(msg)
	blake2b.New512(key)
	blake2s.Sum256(msg)
	md4.New().Write(msg)
	ripemd160.New().Write(msg)

	// Curve25519 and NaCl.
	curve25519.X25519(key, curve25519.Basepoint)
	pub, priv, err := box.GenerateKey(rand.Reader)
	must(err)
	var n24 [24]byte
	var sk [32]byte
	copy(sk[:], key)
	box.Seal(nil, msg, &n24, pub, priv)
	secretbox.Open(nil, secretbox.Seal(nil, msg, &n24, &sk), &n24, &sk)

	// Legacy block ciphers.
	if b, err := blowfish.NewCipher(key[:16]); err == nil {
		b.Encrypt(out[:8], msg[:8])
	}
	if b, err := twofish.NewCipher(key); err == nil {
		b.Encrypt(out[:16], msg[:16])
	}
	if b, err := cast5.NewCipher(key[:16]); err == nil {
		b.Encrypt(out[:8], msg[:8])
	}
	if b, err := tea.NewCipher(key[:16]); err == nil {
		b.Encrypt(out[:8], msg[:8])
	}
	if b, err := xtea.NewCipher(key[:16]); err == nil {
		b.Encrypt(out[:8], msg[:8])
	}

	// SSH: a server and a client handshake over a pipe, password and key auth.
	_, hostPriv, err := ed25519.GenerateKey(rand.Reader)
	must(err)
	hostSigner, err := ssh.NewSignerFromKey(hostPriv)
	must(err)
	scfg := &ssh.ServerConfig{
		PasswordCallback: func(c ssh.ConnMetadata, pw []byte) (*ssh.Permissions, error) { return nil, nil },
		PublicKeyCallback: func(c ssh.ConnMetadata, key ssh.PublicKey) (*ssh.Permissions, error) {
			return nil, nil
		},
	}
	scfg.AddHostKey(hostSigner)
	ccfg := &ssh.ClientConfig{
		User:            "user",
		Auth:            []ssh.AuthMethod{ssh.Password("pw"), ssh.PublicKeys(hostSigner)},
		HostKeyCallback: ssh.FixedHostKey(hostSigner.PublicKey()),
	}
	a, b := net.Pipe()
	go func() {
		conn, chans, reqs, err := ssh.NewServerConn(a, scfg)
		if err != nil {
			return
		}
		go ssh.DiscardRequests(reqs)
		for nc := range chans {
			ch, creqs, err := nc.Accept()
			if err == nil {
				go ssh.DiscardRequests(creqs)
				ch.Close()
			}
		}
		conn.Close()
	}()
	cc, cchans, creqs, err := ssh.NewClientConn(b, "pipe", ccfg)
	if err == nil {
		client := ssh.NewClient(cc, cchans, creqs)
		if sess, err := client.NewSession(); err == nil {
			sess.Run("true")
		}
		client.Dial("tcp", "127.0.0.1:1")
		client.Conn.SendRequest("keepalive@openssh.com", true, nil)
		client.Close()
	}
	fmt.Println(ssh.FingerprintSHA256(hostSigner.PublicKey()),
		string(ssh.MarshalAuthorizedKey(hostSigner.PublicKey())))
}
