# -*- mode: Python -*-

docker_build('meetup_bot', '.')
k8s_yaml('kubernetes.yml')
k8s_resource('meetup_bot', port_forwards=8000)
