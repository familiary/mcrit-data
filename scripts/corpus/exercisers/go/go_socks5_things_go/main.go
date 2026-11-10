// Exerciser for things-go/go-socks5: a Server built with the library's own
// options, authenticators, resolver and rule set, serving one SOCKS5 CONNECT
// over an in-memory pipe, plus the statute wire-format codecs. Built inside
// the module, so github.com/things-go/go-socks5 symbols are the library's.
package main

import (
	"bytes"
	"context"
	"crypto/tls"
	"fmt"
	"io"
	"log"
	"net"
	"os"

	socks5 "github.com/things-go/go-socks5"
	"github.com/things-go/go-socks5/bufferpool"
	"github.com/things-go/go-socks5/statute"
)

func main() {
	creds := socks5.StaticCredentials{"user": "pass"}
	srv := socks5.NewServer(
		socks5.WithAuthMethods([]socks5.Authenticator{
			socks5.UserPassAuthenticator{Credentials: creds},
			socks5.NoAuthAuthenticator{},
		}),
		socks5.WithCredential(creds),
		socks5.WithResolver(socks5.DNSResolver{}),
		socks5.WithRule(socks5.NewPermitConnAndAss()),
		socks5.WithBindIP(net.IPv4zero),
		socks5.WithBufferPool(bufferpool.NewPool(32*1024)),
		socks5.WithLogger(socks5.NewLogger(log.New(io.Discard, "", 0))),
		socks5.WithUseBindIpBaseResolveAsUdpAddr(true),
		socks5.WithDial(func(ctx context.Context, network, addr string) (net.Conn, error) {
			return nil, fmt.Errorf("no dial in exerciser: %s", addr)
		}),
		socks5.WithConnectMiddleware(func(ctx context.Context, w io.Writer, r *socks5.Request) error { return nil }),
		socks5.WithBindMiddleware(func(ctx context.Context, w io.Writer, r *socks5.Request) error { return nil }),
		socks5.WithAssociateMiddleware(func(ctx context.Context, w io.Writer, r *socks5.Request) error { return nil }),
	)

	mr := statute.NewMethodRequest(statute.VersionSocks5, []byte{statute.MethodUserPassAuth})
	req := bytes.NewBuffer(mr.Bytes())
	up := statute.NewUserPassRequest(statute.UserPassAuthVersion, []byte("user"), []byte("pass"))
	req.Write(up.Bytes())
	req.Write([]byte{5, 1, 0, 3, 11})
	req.WriteString("example.com")
	req.Write([]byte{0, 80})

	if r, err := statute.ParseRequest(bytes.NewReader([]byte{5, 1, 0, 1, 127, 0, 0, 1, 0, 80})); err == nil {
		fmt.Println(r.Command, r.DstAddr.String(), r.DstAddr.Address(), r.Bytes())
	}
	if _, err := statute.ParseAddrSpec("example.com:80"); err == nil {
		d, _ := statute.NewDatagram("127.0.0.1:53", []byte("x"))
		statute.ParseDatagram(d.Bytes())
	}
	statute.ParseReply(bytes.NewReader([]byte{5, 0, 0, 1, 0, 0, 0, 0, 0, 0}))
	statute.ParseMethodReply(bytes.NewReader([]byte{5, 2}))
	statute.ParseUserPassReply(bytes.NewReader([]byte{1, 0}))

	a, b := net.Pipe()
	go func() {
		b.Write(req.Bytes())
		io.Copy(io.Discard, b)
		b.Close()
	}()
	fmt.Println(srv.ServeConn(a))
	go srv.ListenAndServe("tcp", "127.0.0.1:0")
	go srv.ListenAndServeTLS("tcp", "127.0.0.1:0", &tls.Config{})
	_ = os.Args
}
