package protocol

import (
	log "github.com/sirupsen/logrus"
	"layeh.com/radius"
)

type Status int

const (
	StatusUnknown Status = iota
	StatusSuccess
	StatusError
	StatusNextProtocol
)

type Context interface {
	Packet() *radius.Request
	RootPayload() Payload

	ProtocolSettings() interface{}

	GetProtocolState(p Type) interface{}
	SetProtocolState(p Type, s interface{})
	IsProtocolStart(p Type) bool

	EndInnerProtocol(Status, func(p *radius.Packet) *radius.Packet)

	Log() *log.Entry
}
