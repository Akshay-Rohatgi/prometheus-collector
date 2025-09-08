{{- define "llm.name" -}}
{{- .Chart.Name | trunc 52 | trimSuffix "-" -}}
{{- end }}

{{- define "llm.fullname" -}}
{{- if .Values.fullnameOverride }}{{ .Values.fullnameOverride }}{{ else }}{{ include "llm.name" . }}{{ end }}
{{- end }}

{{- define "llm.labels" -}}
app: {{ include "llm.fullname" . }}
chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
heritage: Helm
release: {{ .Release.Name }}
{{- end }}
