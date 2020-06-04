# stackwithless

## install on compute nodes
```
easy_install pip
yum install gcc
python -m pip install virtualenv

curl https://dl.fedoraproject.org/pub/epel/7Server/x86_64/Packages/e/epel-release-7-12.noarch.rpm -o epel-release-7-12.noarch.rpm
cd /opt/stackwithless/agent
virtualenv env
source env/bin/activate
pip3 install -r requirements.txt 

docker pull redis
#docker run --name stackwithless -d redis redis-server --appendonly yes -v /opt/stackwithless/db:/data
docker run --name stackwithless -d redis redis-server 


```
