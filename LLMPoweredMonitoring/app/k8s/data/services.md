```java
[
    {
        'api_version': None,
        'kind': None,
        'metadata': {
            'annotations': {
                'meta.helm.sh/release-name': 'azmon-kafka-exporter',
                'meta.helm.sh/release-namespace': 'azmon-kafka-exporter'
            },
            'creation_timestamp': datetime.datetime(2025, 7, 16, 17, 1, 17, tzinfo=tzutc()),
            'deletion_grace_period_seconds': None,
            'deletion_timestamp': None,
            'finalizers': None,
            'generate_name': None,
            'generation': None,
            'labels': {
                'app': 'prometheus-kafka-exporter',
                'app.kubernetes.io/managed-by': 'Helm',
                'chart': 'prometheus-kafka-exporter-2.10.0',
                'heritage': 'Helm',
                'release': 'azmon-kafka-exporter'
            },
            'managed_fields': [
                {
                    'api_version': 'v1',
                    'fields_type': 'FieldsV1',
                    'fields_v1': {
                        'f:metadata': {
                            'f:annotations': {
                                '.': {},
                                'f:meta.helm.sh/release-name': {},
                                'f:meta.helm.sh/release-namespace': {}
                            },
                            'f:labels': {
                                '.': {},
                                'f:app': {},
                                'f:app.kubernetes.io/managed-by': {},
                                'f:chart': {},
                                'f:heritage': {},
                                'f:release': {}
                            }
                        },
                        'f:spec': {
                            'f:internalTrafficPolicy': {},
                            'f:ports': {
                                '.': {},
                                'k:{"port":9308,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                }
                            },
                            'f:selector': {},
                            'f:sessionAffinity': {},
                            'f:type': {}
                        }
                    },
                    'manager': 'helm',
                    'operation': 'Update',
                    'subresource': None,
                    'time': datetime.datetime(2025, 7, 16, 17, 1, 17, tzinfo=tzutc())
                }
            ],
            'name': 'azmon-kafka-exporter-prometheus-kafka-exporter',
            'namespace': 'azmon-kafka-exporter',
            'owner_references': None,
            'resource_version': '9222177',
            'self_link': None,
            'uid': '18d9aeed-adfe-41da-819b-0575e0e20faa'
        },
        'spec': {
            'allocate_load_balancer_node_ports': None,
            'cluster_ip': '10.0.149.192',
            'cluster_i_ps': ['10.0.149.192'],
            'external_i_ps': None,
            'external_name': None,
            'external_traffic_policy': None,
            'health_check_node_port': None,
            'internal_traffic_policy': 'Cluster',
            'ip_families': ['IPv4'],
            'ip_family_policy': 'SingleStack',
            'load_balancer_class': None,
            'load_balancer_ip': None,
            'load_balancer_source_ranges': None,
            'ports': [
                {
                    'app_protocol': None,
                    'name': 'exporter-port',
                    'node_port': None,
                    'port': 9308,
                    'protocol': 'TCP',
                    'target_port': 'exporter-port'
                }
            ],
            'publish_not_ready_addresses': None,
            'selector': {'app': 'prometheus-kafka-exporter', 'release': 'azmon-kafka-exporter'},
            'session_affinity': 'None',
            'session_affinity_config': None,
            'traffic_distribution': None,
            'type': 'ClusterIP'
        },
        'status': {'conditions': None, 'load_balancer': {'ingress': None}}
    },
    {
        'api_version': None,
        'kind': None,
        'metadata': {
            'annotations': None,
            'creation_timestamp': datetime.datetime(2025, 7, 18, 18, 39, 38, tzinfo=tzutc()),
            'deletion_grace_period_seconds': None,
            'deletion_timestamp': None,
            'finalizers': None,
            'generate_name': None,
            'generation': None,
            'labels': {
                'app.kubernetes.io/component': 'rabbitmq',
                'app.kubernetes.io/name': 'hello-world',
                'app.kubernetes.io/part-of': 'rabbitmq'
            },
            'managed_fields': [
                {
                    'api_version': 'v1',
                    'fields_type': 'FieldsV1',
                    'fields_v1': {
                        'f:metadata': {
                            'f:labels': {
                                '.': {},
                                'f:app.kubernetes.io/component': {},
                                'f:app.kubernetes.io/name': {},
                                'f:app.kubernetes.io/part-of': {}
                            },
                            'f:ownerReferences': {
                                '.': {},
                                'k:{"uid":"30c01c03-e6bb-4bce-bc76-239c20badb2b"}': {}
                            }
                        },
                        'f:spec': {
                            'f:internalTrafficPolicy': {},
                            'f:ports': {
                                '.': {},
                                'k:{"port":5672,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:appProtocol': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                },
                                'k:{"port":15672,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:appProtocol': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                },
                                'k:{"port":15692,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:appProtocol': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                }
                            },
                            'f:selector': {},
                            'f:sessionAffinity': {},
                            'f:type': {}
                        }
                    },
                    'manager': 'manager',
                    'operation': 'Update',
                    'subresource': None,
                    'time': datetime.datetime(2025, 7, 18, 18, 39, 38, tzinfo=tzutc())
                }
            ],
            'name': 'hello-world',
            'namespace': 'default',
            'owner_references': [
                {
                    'api_version': 'rabbitmq.com/v1beta1',
                    'block_owner_deletion': True,
                    'controller': True,
                    'kind': 'RabbitmqCluster',
                    'name': 'hello-world',
                    'uid': '30c01c03-e6bb-4bce-bc76-239c20badb2b'
                }
            ],
            'resource_version': '10192494',
            'self_link': None,
            'uid': '788eb7e8-a85b-458f-b0fe-1043df3a1d78'
        },
        'spec': {
            'allocate_load_balancer_node_ports': None,
            'cluster_ip': '10.0.232.34',
            'cluster_i_ps': ['10.0.232.34'],
            'external_i_ps': None,
            'external_name': None,
            'external_traffic_policy': None,
            'health_check_node_port': None,
            'internal_traffic_policy': 'Cluster',
            'ip_families': ['IPv4'],
            'ip_family_policy': 'SingleStack',
            'load_balancer_class': None,
            'load_balancer_ip': None,
            'load_balancer_source_ranges': None,
            'ports': [
                {
                    'app_protocol': 'amqp',
                    'name': 'amqp',
                    'node_port': None,
                    'port': 5672,
                    'protocol': 'TCP',
                    'target_port': 5672
                },
                {
                    'app_protocol': 'http',
                    'name': 'management',
                    'node_port': None,
                    'port': 15672,
                    'protocol': 'TCP',
                    'target_port': 15672
                },
                {
                    'app_protocol': 'prometheus.io/metrics',
                    'name': 'prometheus',
                    'node_port': None,
                    'port': 15692,
                    'protocol': 'TCP',
                    'target_port': 15692
                }
            ],
            'publish_not_ready_addresses': None,
            'selector': {'app.kubernetes.io/name': 'hello-world'},
            'session_affinity': 'None',
            'session_affinity_config': None,
            'traffic_distribution': None,
            'type': 'ClusterIP'
        },
        'status': {'conditions': None, 'load_balancer': {'ingress': None}}
    },
    {
        'api_version': None,
        'kind': None,
        'metadata': {
            'annotations': None,
            'creation_timestamp': datetime.datetime(2025, 7, 18, 18, 39, 38, tzinfo=tzutc()),
            'deletion_grace_period_seconds': None,
            'deletion_timestamp': None,
            'finalizers': None,
            'generate_name': None,
            'generation': None,
            'labels': {
                'app.kubernetes.io/component': 'rabbitmq',
                'app.kubernetes.io/name': 'hello-world',
                'app.kubernetes.io/part-of': 'rabbitmq'
            },
            'managed_fields': [
                {
                    'api_version': 'v1',
                    'fields_type': 'FieldsV1',
                    'fields_v1': {
                        'f:metadata': {
                            'f:labels': {
                                '.': {},
                                'f:app.kubernetes.io/component': {},
                                'f:app.kubernetes.io/name': {},
                                'f:app.kubernetes.io/part-of': {}
                            },
                            'f:ownerReferences': {
                                '.': {},
                                'k:{"uid":"30c01c03-e6bb-4bce-bc76-239c20badb2b"}': {}
                            }
                        },
                        'f:spec': {
                            'f:clusterIP': {},
                            'f:internalTrafficPolicy': {},
                            'f:ports': {
                                '.': {},
                                'k:{"port":4369,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                },
                                'k:{"port":25672,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                }
                            },
                            'f:publishNotReadyAddresses': {},
                            'f:selector': {},
                            'f:sessionAffinity': {},
                            'f:type': {}
                        }
                    },
                    'manager': 'manager',
                    'operation': 'Update',
                    'subresource': None,
                    'time': datetime.datetime(2025, 7, 18, 18, 39, 38, tzinfo=tzutc())
                }
            ],
            'name': 'hello-world-nodes',
            'namespace': 'default',
            'owner_references': [
                {
                    'api_version': 'rabbitmq.com/v1beta1',
                    'block_owner_deletion': True,
                    'controller': True,
                    'kind': 'RabbitmqCluster',
                    'name': 'hello-world',
                    'uid': '30c01c03-e6bb-4bce-bc76-239c20badb2b'
                }
            ],
            'resource_version': '10192489',
            'self_link': None,
            'uid': '4a0fb5fa-f60f-4339-b007-d4a03226c5bd'
        },
        'spec': {
            'allocate_load_balancer_node_ports': None,
            'cluster_ip': 'None',
            'cluster_i_ps': ['None'],
            'external_i_ps': None,
            'external_name': None,
            'external_traffic_policy': None,
            'health_check_node_port': None,
            'internal_traffic_policy': 'Cluster',
            'ip_families': ['IPv4'],
            'ip_family_policy': 'SingleStack',
            'load_balancer_class': None,
            'load_balancer_ip': None,
            'load_balancer_source_ranges': None,
            'ports': [
                {
                    'app_protocol': None,
                    'name': 'epmd',
                    'node_port': None,
                    'port': 4369,
                    'protocol': 'TCP',
                    'target_port': 4369
                },
                {
                    'app_protocol': None,
                    'name': 'cluster-rpc',
                    'node_port': None,
                    'port': 25672,
                    'protocol': 'TCP',
                    'target_port': 25672
                }
            ],
            'publish_not_ready_addresses': True,
            'selector': {'app.kubernetes.io/name': 'hello-world'},
            'session_affinity': 'None',
            'session_affinity_config': None,
            'traffic_distribution': None,
            'type': 'ClusterIP'
        },
        'status': {'conditions': None, 'load_balancer': {'ingress': None}}
    },
    {
        'api_version': None,
        'kind': None,
        'metadata': {
            'annotations': {
                'kubectl.kubernetes.io/last-applied-configuration':
'{"apiVersion":"v1","kind":"Service","metadata":{"annotations":{},"name":"investibots-service","namesp
ace":"default"},"spec":{"ports":[{"port":80,"protocol":"TCP","targetPort":8000}],"selector":{"app":"in
vestibots"},"type":"LoadBalancer"}}\n'
            },
            'creation_timestamp': datetime.datetime(2025, 7, 2, 21, 29, 21, tzinfo=tzutc()),
            'deletion_grace_period_seconds': None,
            'deletion_timestamp': None,
            'finalizers': ['service.kubernetes.io/load-balancer-cleanup'],
            'generate_name': None,
            'generation': None,
            'labels': None,
            'managed_fields': [
                {
                    'api_version': 'v1',
                    'fields_type': 'FieldsV1',
                    'fields_v1': {
                        'f:metadata': {
                            'f:annotations': {
                                '.': {},
                                'f:kubectl.kubernetes.io/last-applied-configuration': {}
                            }
                        },
                        'f:spec': {
                            'f:allocateLoadBalancerNodePorts': {},
                            'f:externalTrafficPolicy': {},
                            'f:internalTrafficPolicy': {},
                            'f:ports': {
                                '.': {},
                                'k:{"port":80,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                }
                            },
                            'f:selector': {},
                            'f:sessionAffinity': {},
                            'f:type': {}
                        }
                    },
                    'manager': 'kubectl-client-side-apply',
                    'operation': 'Update',
                    'subresource': None,
                    'time': datetime.datetime(2025, 7, 2, 21, 29, 21, tzinfo=tzutc())
                },
                {
                    'api_version': 'v1',
                    'fields_type': 'FieldsV1',
                    'fields_v1': {
                        'f:metadata': {
                            'f:finalizers': {
                                '.': {},
                                'v:"service.kubernetes.io/load-balancer-cleanup"': {}
                            }
                        },
                        'f:status': {'f:loadBalancer': {'f:ingress': {}}}
                    },
                    'manager': 'cloud-controller-manager',
                    'operation': 'Update',
                    'subresource': 'status',
                    'time': datetime.datetime(2025, 7, 2, 21, 29, 31, tzinfo=tzutc())
                }
            ],
            'name': 'investibots-service',
            'namespace': 'default',
            'owner_references': None,
            'resource_version': '3094728',
            'self_link': None,
            'uid': 'efd2ceb7-f77a-46f9-bd22-7d4d50dad029'
        },
        'spec': {
            'allocate_load_balancer_node_ports': True,
            'cluster_ip': '10.0.19.179',
            'cluster_i_ps': ['10.0.19.179'],
            'external_i_ps': None,
            'external_name': None,
            'external_traffic_policy': 'Cluster',
            'health_check_node_port': None,
            'internal_traffic_policy': 'Cluster',
            'ip_families': ['IPv4'],
            'ip_family_policy': 'SingleStack',
            'load_balancer_class': None,
            'load_balancer_ip': None,
            'load_balancer_source_ranges': None,
            'ports': [
                {
                    'app_protocol': None,
                    'name': None,
                    'node_port': 31358,
                    'port': 80,
                    'protocol': 'TCP',
                    'target_port': 8000
                }
            ],
            'publish_not_ready_addresses': None,
            'selector': {'app': 'investibots'},
            'session_affinity': 'None',
            'session_affinity_config': None,
            'traffic_distribution': None,
            'type': 'LoadBalancer'
        },
        'status': {
            'conditions': None,
            'load_balancer': {
                'ingress': [
                    {'hostname': None, 'ip': '20.109.144.158', 'ip_mode': 'VIP', 'ports': None}
                ]
            }
        }
    },
    {
        'api_version': None,
        'kind': None,
        'metadata': {
            'annotations': None,
            'creation_timestamp': datetime.datetime(2025, 6, 25, 18, 56, 21, tzinfo=tzutc()),
            'deletion_grace_period_seconds': None,
            'deletion_timestamp': None,
            'finalizers': None,
            'generate_name': None,
            'generation': None,
            'labels': {'component': 'apiserver', 'provider': 'kubernetes'},
            'managed_fields': [
                {
                    'api_version': 'v1',
                    'fields_type': 'FieldsV1',
                    'fields_v1': {
                        'f:metadata': {'f:labels': {'.': {}, 'f:component': {}, 'f:provider': {}}},
                        'f:spec': {
                            'f:clusterIP': {},
                            'f:internalTrafficPolicy': {},
                            'f:ipFamilyPolicy': {},
                            'f:ports': {
                                '.': {},
                                'k:{"port":443,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                }
                            },
                            'f:sessionAffinity': {},
                            'f:type': {}
                        }
                    },
                    'manager': 'kube-apiserver',
                    'operation': 'Update',
                    'subresource': None,
                    'time': datetime.datetime(2025, 6, 25, 18, 56, 21, tzinfo=tzutc())
                }
            ],
            'name': 'kubernetes',
            'namespace': 'default',
            'owner_references': None,
            'resource_version': '211',
            'self_link': None,
            'uid': '5594ad77-57f3-4e3c-bcb9-8c1ec50e5e30'
        },
        'spec': {
            'allocate_load_balancer_node_ports': None,
            'cluster_ip': '10.0.0.1',
            'cluster_i_ps': ['10.0.0.1'],
            'external_i_ps': None,
            'external_name': None,
            'external_traffic_policy': None,
            'health_check_node_port': None,
            'internal_traffic_policy': 'Cluster',
            'ip_families': ['IPv4'],
            'ip_family_policy': 'SingleStack',
            'load_balancer_class': None,
            'load_balancer_ip': None,
            'load_balancer_source_ranges': None,
            'ports': [
                {
                    'app_protocol': None,
                    'name': 'https',
                    'node_port': None,
                    'port': 443,
                    'protocol': 'TCP',
                    'target_port': 443
                }
            ],
            'publish_not_ready_addresses': None,
            'selector': None,
            'session_affinity': 'None',
            'session_affinity_config': None,
            'traffic_distribution': None,
            'type': 'ClusterIP'
        },
        'status': {'conditions': None, 'load_balancer': {'ingress': None}}
    },
    {
        'api_version': None,
        'kind': None,
        'metadata': {
            'annotations': {
                'kubectl.kubernetes.io/last-applied-configuration':
'{"apiVersion":"v1","kind":"Service","metadata":{"annotations":{},"labels":{"app":"prometheus-referenc
e-app"},"name":"prometheus-reference-service","namespace":"default"},"spec":{"ports":[{"name":"weather
-app","port":2112,"protocol":"TCP","targetPort":2112},{"name":"untyped-metrics","port":2113,"protocol"
:"TCP","targetPort":2113},{"name":"python-client","port":2114,"protocol":"TCP","targetPort":2114}],"se
lector":{"app":"prometheus-reference-app"}}}\n'
            },
            'creation_timestamp': datetime.datetime(2025, 6, 25, 22, 17, 45, tzinfo=tzutc()),
            'deletion_grace_period_seconds': None,
            'deletion_timestamp': None,
            'finalizers': None,
            'generate_name': None,
            'generation': None,
            'labels': {'app': 'prometheus-reference-app'},
            'managed_fields': [
                {
                    'api_version': 'v1',
                    'fields_type': 'FieldsV1',
                    'fields_v1': {
                        'f:metadata': {
                            'f:annotations': {
                                '.': {},
                                'f:kubectl.kubernetes.io/last-applied-configuration': {}
                            },
                            'f:labels': {'.': {}, 'f:app': {}}
                        },
                        'f:spec': {
                            'f:internalTrafficPolicy': {},
                            'f:ports': {
                                '.': {},
                                'k:{"port":2112,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                },
                                'k:{"port":2113,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                },
                                'k:{"port":2114,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                }
                            },
                            'f:selector': {},
                            'f:sessionAffinity': {},
                            'f:type': {}
                        }
                    },
                    'manager': 'kubectl-client-side-apply',
                    'operation': 'Update',
                    'subresource': None,
                    'time': datetime.datetime(2025, 6, 25, 22, 17, 45, tzinfo=tzutc())
                }
            ],
            'name': 'prometheus-reference-service',
            'namespace': 'default',
            'owner_references': None,
            'resource_version': '56947',
            'self_link': None,
            'uid': 'ac789e7f-b4c2-4752-8590-47cbb5ab81f0'
        },
        'spec': {
            'allocate_load_balancer_node_ports': None,
            'cluster_ip': '10.0.119.130',
            'cluster_i_ps': ['10.0.119.130'],
            'external_i_ps': None,
            'external_name': None,
            'external_traffic_policy': None,
            'health_check_node_port': None,
            'internal_traffic_policy': 'Cluster',
            'ip_families': ['IPv4'],
            'ip_family_policy': 'SingleStack',
            'load_balancer_class': None,
            'load_balancer_ip': None,
            'load_balancer_source_ranges': None,
            'ports': [
                {
                    'app_protocol': None,
                    'name': 'weather-app',
                    'node_port': None,
                    'port': 2112,
                    'protocol': 'TCP',
                    'target_port': 2112
                },
                {
                    'app_protocol': None,
                    'name': 'untyped-metrics',
                    'node_port': None,
                    'port': 2113,
                    'protocol': 'TCP',
                    'target_port': 2113
                },
                {
                    'app_protocol': None,
                    'name': 'python-client',
                    'node_port': None,
                    'port': 2114,
                    'protocol': 'TCP',
                    'target_port': 2114
                }
            ],
            'publish_not_ready_addresses': None,
            'selector': {'app': 'prometheus-reference-app'},
            'session_affinity': 'None',
            'session_affinity_config': None,
            'traffic_distribution': None,
            'type': 'ClusterIP'
        },
        'status': {'conditions': None, 'load_balancer': {'ingress': None}}
    },
    {
        'api_version': None,
        'kind': None,
        'metadata': {
            'annotations': {
                'meta.helm.sh/release-name': 'rabbitmq',
                'meta.helm.sh/release-namespace': 'default'
            },
            'creation_timestamp': datetime.datetime(2025, 7, 18, 18, 28, 49, tzinfo=tzutc()),
            'deletion_grace_period_seconds': None,
            'deletion_timestamp': None,
            'finalizers': None,
            'generate_name': None,
            'generation': None,
            'labels': {
                'app.kubernetes.io/component': 'messaging-topology-operator',
                'app.kubernetes.io/instance': 'rabbitmq',
                'app.kubernetes.io/managed-by': 'Helm',
                'app.kubernetes.io/name': 'rabbitmq-cluster-operator',
                'app.kubernetes.io/part-of': 'rabbitmq',
                'app.kubernetes.io/version': '1.17.2',
                'helm.sh/chart': 'rabbitmq-cluster-operator-4.4.25'
            },
            'managed_fields': [
                {
                    'api_version': 'v1',
                    'fields_type': 'FieldsV1',
                    'fields_v1': {
                        'f:metadata': {
                            'f:annotations': {
                                '.': {},
                                'f:meta.helm.sh/release-name': {},
                                'f:meta.helm.sh/release-namespace': {}
                            },
                            'f:labels': {
                                '.': {},
                                'f:app.kubernetes.io/component': {},
                                'f:app.kubernetes.io/instance': {},
                                'f:app.kubernetes.io/managed-by': {},
                                'f:app.kubernetes.io/name': {},
                                'f:app.kubernetes.io/part-of': {},
                                'f:app.kubernetes.io/version': {},
                                'f:helm.sh/chart': {}
                            }
                        },
                        'f:spec': {
                            'f:internalTrafficPolicy': {},
                            'f:ports': {
                                '.': {},
                                'k:{"port":443,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                }
                            },
                            'f:selector': {},
                            'f:sessionAffinity': {},
                            'f:type': {}
                        }
                    },
                    'manager': 'helm',
                    'operation': 'Update',
                    'subresource': None,
                    'time': datetime.datetime(2025, 7, 18, 18, 28, 49, tzinfo=tzutc())
                }
            ],
            'name': 'rabbitmq-rabbitmq-messaging-topology-operator-webhook',
            'namespace': 'default',
            'owner_references': None,
            'resource_version': '10188450',
            'self_link': None,
            'uid': '6f5c5ad1-5ac7-4a5d-b73b-6f14803c8290'
        },
        'spec': {
            'allocate_load_balancer_node_ports': None,
            'cluster_ip': '10.0.120.142',
            'cluster_i_ps': ['10.0.120.142'],
            'external_i_ps': None,
            'external_name': None,
            'external_traffic_policy': None,
            'health_check_node_port': None,
            'internal_traffic_policy': 'Cluster',
            'ip_families': ['IPv4'],
            'ip_family_policy': 'SingleStack',
            'load_balancer_class': None,
            'load_balancer_ip': None,
            'load_balancer_source_ranges': None,
            'ports': [
                {
                    'app_protocol': None,
                    'name': 'https',
                    'node_port': None,
                    'port': 443,
                    'protocol': 'TCP',
                    'target_port': 'https-webhook'
                }
            ],
            'publish_not_ready_addresses': None,
            'selector': {
                'app.kubernetes.io/component': 'messaging-topology-operator',
                'app.kubernetes.io/instance': 'rabbitmq',
                'app.kubernetes.io/name': 'rabbitmq-cluster-operator'
            },
            'session_affinity': 'None',
            'session_affinity_config': None,
            'traffic_distribution': None,
            'type': 'ClusterIP'
        },
        'status': {'conditions': None, 'load_balancer': {'ingress': None}}
    },
    {
        'api_version': None,
        'kind': None,
        'metadata': {
            'annotations': {
                'strimzi.io/discovery': '[ {\n  "port" : 9092,\n  "tls" : false,\n  "protocol" :
"kafka",\n  "auth" : "none"\n}, {\n  "port" : 9093,\n  "tls" : true,\n  "protocol" : "kafka",\n
"auth" : "none"\n} ]'
            },
            'creation_timestamp': datetime.datetime(2025, 6, 26, 23, 36, 17, tzinfo=tzutc()),
            'deletion_grace_period_seconds': None,
            'deletion_timestamp': None,
            'finalizers': None,
            'generate_name': None,
            'generation': None,
            'labels': {
                'app.kubernetes.io/instance': 'my-cluster',
                'app.kubernetes.io/managed-by': 'strimzi-cluster-operator',
                'app.kubernetes.io/name': 'kafka',
                'app.kubernetes.io/part-of': 'strimzi-my-cluster',
                'strimzi.io/cluster': 'my-cluster',
                'strimzi.io/component-type': 'kafka',
                'strimzi.io/discovery': 'true',
                'strimzi.io/kind': 'Kafka',
                'strimzi.io/name': 'my-cluster-kafka'
            },
            'managed_fields': [
                {
                    'api_version': 'v1',
                    'fields_type': 'FieldsV1',
                    'fields_v1': {
                        'f:metadata': {
                            'f:annotations': {'.': {}, 'f:strimzi.io/discovery': {}},
                            'f:labels': {
                                '.': {},
                                'f:app.kubernetes.io/instance': {},
                                'f:app.kubernetes.io/managed-by': {},
                                'f:app.kubernetes.io/name': {},
                                'f:app.kubernetes.io/part-of': {},
                                'f:strimzi.io/cluster': {},
                                'f:strimzi.io/component-type': {},
                                'f:strimzi.io/discovery': {},
                                'f:strimzi.io/kind': {},
                                'f:strimzi.io/name': {}
                            },
                            'f:ownerReferences': {
                                '.': {},
                                'k:{"uid":"a3e8628d-2c1d-4f40-8561-8721c3035d32"}': {}
                            }
                        },
                        'f:spec': {
                            'f:internalTrafficPolicy': {},
                            'f:ports': {
                                '.': {},
                                'k:{"port":9091,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                },
                                'k:{"port":9092,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                },
                                'k:{"port":9093,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                }
                            },
                            'f:selector': {},
                            'f:sessionAffinity': {},
                            'f:type': {}
                        }
                    },
                    'manager': 'strimzi-cluster-operator',
                    'operation': 'Update',
                    'subresource': None,
                    'time': datetime.datetime(2025, 6, 26, 23, 36, 17, tzinfo=tzutc())
                }
            ],
            'name': 'my-cluster-kafka-bootstrap',
            'namespace': 'kafka',
            'owner_references': [
                {
                    'api_version': 'kafka.strimzi.io/v1beta2',
                    'block_owner_deletion': False,
                    'controller': False,
                    'kind': 'Kafka',
                    'name': 'my-cluster',
                    'uid': 'a3e8628d-2c1d-4f40-8561-8721c3035d32'
                }
            ],
            'resource_version': '476967',
            'self_link': None,
            'uid': 'd74c0639-6927-46ea-b395-3b14f7af6a85'
        },
        'spec': {
            'allocate_load_balancer_node_ports': None,
            'cluster_ip': '10.0.199.175',
            'cluster_i_ps': ['10.0.199.175'],
            'external_i_ps': None,
            'external_name': None,
            'external_traffic_policy': None,
            'health_check_node_port': None,
            'internal_traffic_policy': 'Cluster',
            'ip_families': ['IPv4'],
            'ip_family_policy': 'SingleStack',
            'load_balancer_class': None,
            'load_balancer_ip': None,
            'load_balancer_source_ranges': None,
            'ports': [
                {
                    'app_protocol': None,
                    'name': 'tcp-replication',
                    'node_port': None,
                    'port': 9091,
                    'protocol': 'TCP',
                    'target_port': 9091
                },
                {
                    'app_protocol': None,
                    'name': 'tcp-clients',
                    'node_port': None,
                    'port': 9092,
                    'protocol': 'TCP',
                    'target_port': 9092
                },
                {
                    'app_protocol': None,
                    'name': 'tcp-clientstls',
                    'node_port': None,
                    'port': 9093,
                    'protocol': 'TCP',
                    'target_port': 9093
                }
            ],
            'publish_not_ready_addresses': None,
            'selector': {
                'strimzi.io/broker-role': 'true',
                'strimzi.io/cluster': 'my-cluster',
                'strimzi.io/kind': 'Kafka',
                'strimzi.io/name': 'my-cluster-kafka'
            },
            'session_affinity': 'None',
            'session_affinity_config': None,
            'traffic_distribution': None,
            'type': 'ClusterIP'
        },
        'status': {'conditions': None, 'load_balancer': {'ingress': None}}
    },
    {
        'api_version': None,
        'kind': None,
        'metadata': {
            'annotations': None,
            'creation_timestamp': datetime.datetime(2025, 6, 26, 23, 36, 18, tzinfo=tzutc()),
            'deletion_grace_period_seconds': None,
            'deletion_timestamp': None,
            'finalizers': None,
            'generate_name': None,
            'generation': None,
            'labels': {
                'app.kubernetes.io/instance': 'my-cluster',
                'app.kubernetes.io/managed-by': 'strimzi-cluster-operator',
                'app.kubernetes.io/name': 'kafka',
                'app.kubernetes.io/part-of': 'strimzi-my-cluster',
                'strimzi.io/cluster': 'my-cluster',
                'strimzi.io/component-type': 'kafka',
                'strimzi.io/kind': 'Kafka',
                'strimzi.io/name': 'my-cluster-kafka'
            },
            'managed_fields': [
                {
                    'api_version': 'v1',
                    'fields_type': 'FieldsV1',
                    'fields_v1': {
                        'f:metadata': {
                            'f:labels': {
                                '.': {},
                                'f:app.kubernetes.io/instance': {},
                                'f:app.kubernetes.io/managed-by': {},
                                'f:app.kubernetes.io/name': {},
                                'f:app.kubernetes.io/part-of': {},
                                'f:strimzi.io/cluster': {},
                                'f:strimzi.io/component-type': {},
                                'f:strimzi.io/kind': {},
                                'f:strimzi.io/name': {}
                            },
                            'f:ownerReferences': {
                                '.': {},
                                'k:{"uid":"a3e8628d-2c1d-4f40-8561-8721c3035d32"}': {}
                            }
                        },
                        'f:spec': {
                            'f:clusterIP': {},
                            'f:internalTrafficPolicy': {},
                            'f:ports': {
                                '.': {},
                                'k:{"port":8443,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                },
                                'k:{"port":9090,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                },
                                'k:{"port":9091,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                },
                                'k:{"port":9092,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                },
                                'k:{"port":9093,"protocol":"TCP"}': {
                                    '.': {},
                                    'f:name': {},
                                    'f:port': {},
                                    'f:protocol': {},
                                    'f:targetPort': {}
                                }
                            },
                            'f:publishNotReadyAddresses': {},
                            'f:selector': {},
                            'f:sessionAffinity': {},
                            'f:type': {}
                        }
                    },
                    'manager': 'strimzi-cluster-operator',
                    'operation': 'Update',
                    'subresource': None,
                    'time': datetime.datetime(2025, 6, 26, 23, 36, 18, tzinfo=tzutc())
                }
            ],
            'name': 'my-cluster-kafka-brokers',
            'namespace': 'kafka',
            'owner_references': [
                {
                    'api_version': 'kafka.strimzi.io/v1beta2',
                    'block_owner_deletion': False,
                    'controller': False,
                    'kind': 'Kafka',
                    'name': 'my-cluster',
                    'uid': 'a3e8628d-2c1d-4f40-8561-8721c3035d32'
                }
            ],
            'resource_version': '476970',
            'self_link': None,
            'uid': '21dc1698-aae3-4d09-8e25-c8d9d0730337'
        },
        'spec': {
            'allocate_load_balancer_node_ports': None,
            'cluster_ip': 'None',
            'cluster_i_ps': ['None'],
            'external_i_ps': None,
            'external_name': None,
            'external_traffic_policy': None,
            'health_check_node_port': None,
            'internal_traffic_policy': 'Cluster',
            'ip_families': ['IPv4'],
            'ip_family_policy': 'SingleStack',
            'load_balancer_class': None,
            'load_balancer_ip': None,
            'load_balancer_source_ranges': None,
            'ports': [
                {
                    'app_protocol': None,
                    'name': 'tcp-ctrlplane',
                    'node_port': None,
                    'port': 9090,
                    'protocol': 'TCP',
                    'target_port': 9090
                },
                {
                    'app_protocol': None,
                    'name': 'tcp-replication',
                    'node_port': None,
                    'port': 9091,
                    'protocol': 'TCP',
                    'target_port': 9091
                },
                {
                    'app_protocol': None,
                    'name': 'tcp-kafkaagent',
                    'node_port': None,
                    'port': 8443,
                    'protocol': 'TCP',
                    'target_port': 8443
                },
                {
                    'app_protocol': None,
                    'name': 'tcp-clients',
                    'node_port': None,
                    'port': 9092,
                    'protocol': 'TCP',
                    'target_port': 9092
                },
                {
                    'app_protocol': None,
                    'name': 'tcp-clientstls',
                    'node_port': None,
                    'port': 9093,
                    'protocol': 'TCP',
                    'target_port': 9093
                }
            ],
            'publish_not_ready_addresses': True,
            'selector': {
                'strimzi.io/cluster': 'my-cluster',
                'strimzi.io/kind': 'Kafka',
                'strimzi.io/name': 'my-cluster-kafka'
            },
            'session_affinity': 'None',
            'session_affinity_config': None,
            'traffic_distribution': None,
            'type': 'ClusterIP'
        },
        'status': {'conditions': None, 'load_balancer': {'ingress': None}}
    }
]
```