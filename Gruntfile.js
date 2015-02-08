module.exports = function(grunt) {
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        sass: {
            dist: {
                options: {
                    style: 'compressed'
                },
                files: {
                    'blender-today/application/static/css/main.css': 'blender-today/application/static/sass/main.sass'
                }
            }
        },

        autoprefixer: {
            no_dest: { src: 'blender-today/application/static/css/main.css' }
        },

        watch: {
            files: ['blender-today/application/static/sass/main.sass'],
            tasks: ['sass', 'autoprefixer'],
        }
    });

    grunt.loadNpmTasks('grunt-contrib-sass');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-autoprefixer');

    grunt.registerTask('default', ['sass', 'autoprefixer']);
};
