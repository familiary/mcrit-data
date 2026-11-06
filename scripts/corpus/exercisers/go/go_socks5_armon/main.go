// Exerciser for armon/go-socks5: a Server configured with the library's own
// authenticators, credential store, resolver and rule set, serving one
// SOCKS5 CONNECT over an in-memory pipe. The upstream tree is pre-modules, so
// the recipe adds go.mod and go.sum from this directory beside it.
package main

import (
	"bytes"
	"fmt"
	"io"
	"log"
	"net"
	"os"

	"github.com/armon/go-socks5"
	"golang.org/x/net/context"
)

func main() {
	creds := socks5.StaticCredentials{"user": "pass"}
	conf := &socks5.Config{
		AuthMethods: []socks5.Authenticator{
			socks5.UserPassAuthenticator{Credentials: creds},
			socks5.NoAuthAuthenticator{},
		},
		Credentials: creds,
		Resolver:    socks5.DNSResolver{},
		Rules:       socks5.PermitAll(),
		BindIP:      net.IPv4zero,
		Logger:      log.New(io.Discard, "", 0),
		Dial: func(ctx context.Context, network, addr string) (net.Conn, error) {
			return nil, fmt.Errorf("no dial in exerciser: %s", addr)
		},
	}
	conf.Rules = &socks5.PermitCommand{EnableConnect: true, EnableBind: true, EnableAssociate: true}
	srv, err := socks5.New(conf)
	if err != nil {
		os.Exit(1)
	}

	// Greeting offering user/pass, credentials, then CONNECT example.com:80.
	req := bytes.NewBuffer([]byte{5, 1, 2, 1, 4, 'u', 's', 'e', 'r', 4, 'p', 'a', 's', 's'})
	req.Write([]byte{5, 1, 0, 3, 11})
	req.WriteString("example.com")
	req.Write([]byte{0, 80})
	if r, err := socks5.NewRequest(bytes.NewReader(req.Bytes()[14:])); err == nil {
		fmt.Println(r.Command, r.DestAddr, r.DestAddr.String(), r.DestAddr.Address())
	}
	a, b := net.Pipe()
	go func() {
		b.Write(req.Bytes())
		io.Copy(io.Discard, b)
		b.Close()
	}()
	fmt.Println(srv.ServeConn(a))
	go srv.ListenAndServe("tcp", "127.0.0.1:0")
}
