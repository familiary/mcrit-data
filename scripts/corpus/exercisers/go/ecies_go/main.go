// Exerciser for ecies/go: key generation, hex and byte round-trips, ECDH,
// encapsulate/decapsulate and Encrypt/Decrypt, the surface a ransomware key
// wrapper calls. Built inside the module (CGO_ENABLED=0 selects the
// secp256k1 implementation from decred, not go-ethereum's C one).
package main

import (
	"fmt"
	"os"

	ecies "github.com/ecies/go/v2"
)

func main() {
	k, err := ecies.GenerateKey()
	if err != nil {
		os.Exit(1)
	}
	k2, err := ecies.NewPrivateKeyFromHex(k.Hex())
	if err != nil {
		os.Exit(1)
	}
	fmt.Println(k.Equals(k2), k.PublicKey.Equals(k2.PublicKey), k2.Bytes())
	pub, err := ecies.NewPublicKeyFromHex(k.PublicKey.Hex(true))
	if err != nil {
		pub, _ = ecies.NewPublicKeyFromBytes(k.PublicKey.Bytes(false))
	}
	k3 := ecies.NewPrivateKeyFromBytes(k.Bytes())
	secret, _ := k3.Encapsulate(pub)
	shared, _ := pub.Decapsulate(k)
	ecdh, _ := k.ECDH(pub)
	fmt.Println(len(secret), len(shared), len(ecdh))
	ct, err := ecies.Encrypt(pub, []byte("per-file key"))
	if err != nil {
		os.Exit(1)
	}
	pt, err := ecies.Decrypt(k, ct)
	fmt.Println(string(pt), err)
}
