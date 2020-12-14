$(document).ready(function() {
    $('.info').hide()
    // Initialize the Amazon Cognito credentials provider
    $('#stop-button').hide();
    AWS.config.update({
        credentials: new AWS.CognitoIdentityCredentials({
            IdentityPoolId: 'us-east-1:77379cb4-0a21-40b7-9eb8-bd30b979f294'
        }),
        region: 'us-east-1'
    });
    $("#file-upload").change(function(){
        //submit the form here
        var files = document.getElementById('file-upload').files;
        console.log(files)

        for(let i=0, file; file=files[i]; i++){
            var reader = new FileReader();
            reader.onload = function(e) {
                console.log("reading of" + file.name)
                let fileName = file.name;
                let imagebase64 = e.target.result.replace(/^data:image\/(png|jpg|jpeg);base64,/,"");
                uploadImage(imagebase64, fileName).
                then((response) => {
                    console.log("Response", response);

                })
                .catch((error) => {
                    console.log('An error occurred while uploading image', error);
                });
            };
            console.log("handling of " + file.name)
            reader.readAsDataURL(file);
        }
        $(".info").text(files.length + " file(s) uploaded successfully");
        $('#file-upload').val('')
        $('.info').show()

    });

    $('.upload-button').click(function(){
        $('#file-upload').trigger('click');
    });

    $('.main').click(function(){
        $('.info').hide()
    });

    $('.search-button').click(function(){
        const input = $('#search-input').val();
        if ($.trim(input) === '') {
            return false;
        }
        $('#search-input').val('');
        console.log(input)
        searchImages(input).
        then((response) => {
            $('.images').html('');
            console.log("Response", response);
            res = response["data"]["results"];
            if(res === undefined){
                console.log("Result undefined");
            } else {
                console.log(res.length + "images found");
                $('.images').append('<p>' + res.length + ' search results for <b>' + input + '</b></p>');
                for(i=0;i<res.length;i++){
                    console.log(res[i]['url']);
                    $(".images").append("" +
                        "<img src='" +
                        res[i]['url'] +
                        "' class = 'p-2' style='height: 200px;width: 220px'/>");
                }
            }
        })
        .catch((error) => {
            console.log('An error occurred while searching images', error);
        });


    });
    function uploadImage(image, filename) {
        return sdk.uploadFilenamePut(
            {'filename': filename},
            image,
            {});
    }

    function searchImages(query) {
        return sdk.searchGet(
            {},
             {},
            {queryParams: {
                    'q': query
                }});
    }
});
