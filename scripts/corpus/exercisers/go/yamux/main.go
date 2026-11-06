// Exerciser for hashicorp/yamux: a Server/Client pair over an in-memory pipe,
// one stream opened and echoed, plus the rest of the exported surface so the
// linker keeps it. Built inside the yamux module, so every github.com/hashicorp/
// yamux symbol in the image is the library's own.
package main

import (
	"context"
	"fmt"
	"io"
	"net"
	"os"
	"time"

	"github.com/hashicorp/yamux"
)

func main() {
	a, b := net.Pipe()
	cfg := yamux.DefaultConfig()
	cfg.EnableKeepAlive = true
	cfg.KeepAliveInterval = time.Second
	cfg.LogOutput = io.Discard
	if err := yamux.VerifyConfig(cfg); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	server, err := yamux.Server(a, cfg)
	if err != nil {
		os.Exit(1)
	}
	client, err := yamux.Client(b, cfg)
	if err != nil {
		os.Exit(1)
	}

	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), time.Second)
		defer cancel()
		s, err := server.AcceptStreamWithContext(ctx)
		if err != nil {
			s, err = server.AcceptStream()
			if err != nil {
				return
			}
		}
		io.Copy(s, s)
		s.Close()
		if c, err := server.Accept(); err == nil {
			c.Close()
		}
	}()

	st, err := client.OpenStream()
	if err != nil {
		os.Exit(1)
	}
	st.SetDeadline(time.Now().Add(time.Second))
	st.SetReadDeadline(time.Now().Add(time.Second))
	st.SetWriteDeadline(time.Now().Add(time.Second))
	st.Write([]byte("hello"))
	buf := make([]byte, 5)
	st.Read(buf)
	fmt.Println(st.StreamID(), st.Session() == client, st.LocalAddr(), st.RemoteAddr())
	st.Shrink()
	rtt, _ := client.Ping()
	fmt.Println(rtt, client.NumStreams(), client.IsClosed(), client.Addr(),
		client.LocalAddr(), client.RemoteAddr())
	if c, err := client.Open(); err == nil {
		c.Close()
	}
	st.Close()
	client.GoAway()
	select {
	case <-client.CloseChan():
	default:
	}
	client.Close()
	server.Close()
	fmt.Println(yamux.ErrSessionShutdown, yamux.ErrStreamClosed, yamux.ErrTimeout)
}
