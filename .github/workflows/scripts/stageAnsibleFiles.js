
module.exports = ({context}) => {
          const changed_ansible_files = context.steps.changed-ansible-files.outputs.all_changed_files
          if (changed_ansible_files.length > 0) {
            console.log(`Changed Python files: ${changed_ansible_files}`)
            github.actions.setSecret({
              name: 'CHANGED_ANSIBLE_FILES',
              value: changed_ansible_files
            })
          } else {
            console.log('No changed Ansible files')
          }
};