from qubesadmin.tests import TestVM, TestVMCollection


def new_mock_qapp(app):
    app.domains = TestVMCollection(
        [
            ('dom0', TestVM('dom0', klass='AdminVM', label='black',
                            icon='adminvm-black', features={})),
            ('test-vm',
             TestVM('test-vm', klass='AppVM', label='blue', icon='appvm-blue',
                    netvm=TestVM('sys-firewall'), template=TestVM('template'),
                    features={})),
            ('sys-firewall',
             TestVM('sys-firewall', klass='DisposableVM', label='green',
                    icon='servicevm-green', netvm=TestVM('sys-net'),
                    template=TestVM('template'), features={})),
            ('sys-net',
             TestVM('sys-net', klass='StandaloneVM', label='red',
                    icon='servicevm-red', provides_network=True,
                    template=TestVM('template'), features={'servicevm': 1})),
            ('template',
             TestVM('template', klass='TemplateVM', label='red',
                    icon='templatevm-red', features={})),
            ('template-dvm',
             TestVM('template-dvm', klass='AppVM', label='red',
                    icon='templatevm-red', template_for_dispvms=True,
                    netvm=TestVM('sys-net'), template=TestVM('template'),
                    features={})),
        ]
    )
    return app
