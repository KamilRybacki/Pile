
module.exports = ({context}) => {
          const changed_python_files = context.steps.changed-python-files.outputs.all_changed_files
          if (changed_python_files.length > 0) {
            console.log(`Changed Python files: ${changed_python_files}`)
            github.actions.setSecret({
              name: 'CHANGED_PYTHON_FILES',
              value: changed_python_files
            })
          } else {
            console.log('No changed Python files')
          }
};
