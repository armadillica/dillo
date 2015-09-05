module.exports = function(grunt) {
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        jade: {
          compile: {
            options: {
              data: {
                debug: false
              },
              pretty: false,
            },
            files: [{
              expand: true,
              cwd: 'dillo/src/templates',
              src: [ '**/*.jade' ],
              dest: 'dillo/application/templates',
              ext: '.html'
            }]
          }
        },


        sass: {
            dist: {
                options: {
                    style: 'compressed'
                },
                files: {
                    'dillo/application/static/css/main.css': 'dillo/src/styles/main.sass'
                }
            }
        },

        uglify: {
            all_src : {
              src : 'dillo/src/scripts/uglify/*.js',
              dest : 'dillo/application/static/js/theuniverse.min.js'
            }
        },

        autoprefixer: {
            no_dest: { src: 'dillo/application/static/css/main.css' }
        },

        watch: {
            files: ['dillo/src/styles/main.sass'],
            js:  { files: 'dillo/src/scripts/uglify/*.js', tasks: [ 'uglify' ] },
            tasks: ['sass', 'autoprefixer', 'uglify', 'jade'],
            jade: {
              files: 'dillo/src/templates/**/*.jade',
              tasks: [ 'jade' ]
            },
            options: {
              livereload: true,
            },
        }
    });

    grunt.loadNpmTasks('grunt-contrib-sass');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-contrib-jade');
    grunt.loadNpmTasks('grunt-autoprefixer');

    grunt.registerTask('default', ['sass', 'autoprefixer', 'uglify', 'jade']);
};
