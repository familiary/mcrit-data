// Exerciser for zema1/suo5 v2.1.0: the client's own packages (suo5, ctrl,
// netrans) driven through the exported entry points the CLI uses - the
// default config, ctrl.Run (Connect, the chunked/half-chunked/classic stream
// factories, the SOCKS5 and forward handlers) and the netrans frame codec and
// readers. It is the CLI minus flag parsing, built inside the module so every
// github.com/zema1/suo5 symbol in the image is the project's.
package main

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"time"

	"github.com/zema1/suo5/ctrl"
	"github.com/zema1/suo5/netrans"
	"github.com/zema1/suo5/suo5"
)

func main() {
	conf := suo5.DefaultSuo5Config()
	conf.Target = "http://127.0.0.1:1/suo5.jsp"
	conf.Mode = suo5.AutoDuplex
	conf.Timeout = 1
	conf.RawHeader = []string{"Cookie: a=b"}
	conf.ExcludeDomain = []string{"*.example.com"}
	conf.EnableCookieJar = true
	conf.OnRemoteConnected = func(e *suo5.ConnectedEvent) {}
	conf.GuiLog = io.Discard
	if err := conf.Parse(); err != nil {
		fmt.Println(err)
	}
	fmt.Println(conf.HeaderString(), conf.NoAuth(), conf.TimeoutTime())
	for _, m := range []suo5.ConnectionType{suo5.AutoDuplex, suo5.FullDuplex, suo5.HalfDuplex, suo5.Classic} {
		conf.Mode = m
		suo5.NewRawHttpClient(conf.UpstreamProxy, time.Second, time.Second)
		suo5.NewHttpTransport(conf.UpstreamProxy, time.Second)
	}

	frame := netrans.NewDataFrame([]byte("hello"))
	if f, err := netrans.ReadFrame(bytes.NewReader(frame.MarshalBinary())); err == nil {
		fmt.Println(len(f.Data))
	}
	netrans.ReadFrameBase64(bytes.NewReader(frame.MarshalBinaryBase64()))
	ch, w := netrans.NewChannelWriteCloser(context.Background())
	w.Write([]byte("x"))
	r := netrans.NewTimeoutReader(context.Background(), netrans.NewChannelReader(ch), time.Millisecond)
	r.Read(make([]byte, 1))
	netrans.MultiReadCloser(netrans.NewTimeoutReadCloser(context.Background(), io.NopCloser(bytes.NewReader(nil)), time.Second)).Close()
	netrans.OffsetReader(netrans.NoOpReader(bytes.NewReader(nil)), 1)
	speed := netrans.NewSpeedCaculator()
	speed.AddSpeed(1, 2)
	fmt.Println(speed.Statistic())

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if err := ctrl.Run(ctx, conf); err != nil {
		fmt.Fprintln(os.Stderr, err)
	}
}
