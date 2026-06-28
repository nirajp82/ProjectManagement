$ErrorActionPreference = "Stop"

$appName = "pm-app"

docker rm -f $appName *>$null
