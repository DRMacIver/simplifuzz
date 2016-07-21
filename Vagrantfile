# -*- mode: ruby -*-
# vi: set ft=ruby :

# This is a trivial Vagrantfile designed to simplify development of Hypothesis on Windows,
# where the normal make based build system doesn't work, or anywhere else where you would
# prefer a clean environment for Hypothesis development. It doesn't do anything more than spin
# up a suitable local VM for use with vagrant ssh. You should then use the Makefile from within
# that VM.

PROVISION = <<PROVISION

sudo apt-get update
sudo apt-get install -y git libreadline-dev libssl-dev zlib1g-dev build-essential libbz2-dev libsqlite3-dev curl

if [ ! -d ~/.pyenv ]; then
    git clone https://github.com/yyuu/pyenv.git ~/.pyenv
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
    echo 'eval "$(pyenv init -)"' >> ~/.bash_profile
fi

PROVISION

Vagrant.configure(2) do |config|

  config.vm.provider "virtualbox" do |v|
    v.memory = 1024
  end

  config.vm.provider "vmware_workstation" do |v|
    v.vmx["memsize"] = "1024"
    v.vmx["numvcpus"] = "2"
  end

  config.vm.box = "bento/ubuntu-14.04"

  config.vm.provision "shell", inline: PROVISION, privileged: false
end
