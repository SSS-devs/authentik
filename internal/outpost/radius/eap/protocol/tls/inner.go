package tls

import (
	"goauthentik.io/internal/outpost/radius/eap/protocol"
)

func (p *Payload) innerHandler(ctx protocol.Context) {
	d := make([]byte, 1024)
	if !ctx.IsProtocolStart(p.Inner.Type()) {
		ctx.Log().Debug("TLS: Reading from TLS for inner protocol")
		_, err := p.st.TLS.Read(d)
		if err != nil {
			ctx.Log().WithError(err).Warning("TLS: Failed to read from TLS connection")
		}
	}
	err := p.Inner.Decode(d)
	if err != nil {
		ctx.Log().WithError(err).Warning("TLS: failed to decode inner protocol")
		ctx.EndInnerProtocol(protocol.StatusError, nil)
		return
	}
	pl := p.Inner.Handle(ctx)
	enc, err := pl.Encode()
	if err != nil {
		ctx.Log().WithError(err).Warning("TLS: failed to encode inner protocol")
		ctx.EndInnerProtocol(protocol.StatusError, nil)
		return
	}
	_, err = p.st.TLS.Write(enc)
	if err != nil {
		ctx.Log().WithError(err).Warning("TLS: failed to write to TLS")
		ctx.EndInnerProtocol(protocol.StatusError, nil)
		return
	}
}
