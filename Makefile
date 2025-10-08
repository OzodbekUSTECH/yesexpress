-include .env.makefile
export


.PHONY: ssh
ssh:
	ssh $(SSH_USER)@$(SSH_HOST)

.PHONY: ci
ci:
	rsync -ova . $(SSH_USER)@$(SSH_HOST):/app --exclude '.git'  --exclude '.idea' --exclude '.mypy_cache' --exclude '.venv' --delete
