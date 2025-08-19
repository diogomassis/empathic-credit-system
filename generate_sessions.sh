cd k6/register-users/ && k6 run --out json=../results.json load-test.js && node process-results.js && cd ../login-users/ && k6 run --out json=../results-lo
gin.json login-test.js && node process-logins.js && cd ../..
